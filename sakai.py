import mysql.connector
from zeep import Client
import uuid
import logging
from xml.etree import ElementTree as ET

server_url = "https://sakai-t.brocku.ca"
# server_url = "https://lms.brocku.ca"

loginUrl = server_url + "/sakai-ws/soap/login?wsdl"
scriptUrl = server_url + "/sakai-ws/soap/sakai?wsdl"
longsightScriptUrl = server_url + "/sakai-ws/soap/longsight?wsdl"

login_proxy = Client(loginUrl)
script_proxy = Client(scriptUrl)
longsight_proxy = Client(longsightScriptUrl)


#
# def sakai_log():
# 	logs = logging.getLogger("sakai")
# 	fh = logging.FileHandler('logs.log')
# 	logs.setLevel(logging.DEBUG)
# 	fh.setLevel(logging.DEBUG)
# 	formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# 	fh.setFormatter(formatter)
# 	logs.addHandler(fh)
# 	return logs


def generate_site_id():
	return uuid.uuid1()


def create_sakai_site(db_conn_params, params, config, session_id):

	if params[2] == 'False':
		if params[4] != None:
			script_proxy.service.changeSitePublishStatus(session_id, params[4], False)
			add_remove_users(db_conn_params, session_id, params[4], params[0])
		else:
			return
	else:
		if params[4] != None:
			script_proxy.service.changeSitePublishStatus(session_id, params[4], True)
			add_remove_users(db_conn_params, session_id, params[4], params[0])
		else:
			new_site_id = generate_site_id()

			site_description = f"""<center><p><strong> {params[1]} is being offered in Brightspace this term!</strong> Use the button 
									on this page to continue to this course in Brightspace.</p>
									<p>&nbsp;</p>
									<p style='text-align:center'><button><span class='Mrphs-itemTitle'>
									<a href='https://brocku.brightspace.com/d2l/home/{params[0]}' rel='noopener' target='_blank' 
									title='Open this course in Brightspace'>Open this course in Brightspace</a></span></button></p></center>"""

			script_proxy.service.addNewSite(session_id, new_site_id, params[1], site_description,
													   params[1], "", "", False, "", True, True, "", "course")

			add_sakai_site_to_DB(db_conn_params, params[0], new_site_id)

			script_proxy.service.setSiteProperty(session_id, new_site_id, "term", config["current_term"])
			script_proxy.service.setSiteProperty(session_id, new_site_id, "term_eid", config["current_term_eid"])

			script_proxy.service.addToolAndPageToSite(session_id, new_site_id, "sakai.siteinfo",
																		   "Site Info", "Site Info", 0, 0, False)
			script_proxy.service.addToolAndPageToSite(session_id, new_site_id, "sakai.iframe.site",
																		  "Open Brightspace", "", 0, 0, False)

			script_proxy.service.addConfigPropertyToPage(session_id, new_site_id, "Overview",
																					 "is_home_page", True)

			add_remove_users(db_conn_params, session_id, new_site_id, params[0])


def add_sakai_site_to_DB(db_conn_params, org_unit_id, site_id):
	with mysql.connector.connect(**db_conn_params) as conn:
		with conn.cursor(buffered=True) as cur:
			cur.execute(f"""insert into sakai_sites (org_unit_id, site_id)
							values ({org_unit_id}, '{site_id}');""")
		conn.commit()

def add_remove_users(db_conn_params, session_id, site_id, org_unit_id):
	roles = {
		110: "Student",
		109: "Instructor",
		111: "Audit",
		105: "Instructor",
		113: "Instructor",
		114: "Instructor",
		116: "Instructor",
		121: "Teaching Assistant",
		122: "Instructor",
		118: "Instructor",
		123: "Instructor"
	}
	with mysql.connector.connect(**db_conn_params) as conn:
		with conn.cursor(buffered=True) as cur:
			cur.execute(f"""select u.user_name, e.action, e.role_id
							from tmp_enroll_withdrawals e
							left join users u
							on e.user_id = u.user_id
							where e.org_unit_id = {org_unit_id};""")
			class_list = cur.fetchall()
			# students = ",".join([each[0] for each in class_list if each[2] == 110])
			# instructors = ",".join([each[0] for each in class_list if each[2] == 109 or each[2] == 105 or each[2] == 114 or each[2] == 116 or each[2] == 113])
			# audits = ",".join([each[0] for each in class_list if each[2] == 111])
			# script_proxy.service.addMemberToSiteWithRoleBatch(session_id, site_id, students, "Student")
			# script_proxy.service.addMemberToSiteWithRoleBatch(session_id, site_id, instructors, "Instructor")
			# script_proxy.service.addMemberToSiteWithRoleBatch(session_id, site_id, audits, "Audit")
			for user in class_list:
				if not user:
					continue
				if user[1] == 'Enroll':
					script_proxy.service.addMemberToSiteWithRole(session_id, site_id, user[0], roles[user[2]])
				else:
					script_proxy.service.removeMemberFromSite(session_id, site_id, user[0])

def drop_tmp_tables(db_conn_params):
	with mysql.connector.connect(**db_conn_params) as conn:
		with conn.cursor(buffered=True) as cur:
			cur.execute(f"show tables;")
			all_tables = cur.fetchall()

			for each in all_tables:
				if each[0].startswith('tmp'):
					cur.execute(f"drop table {each[0]};")


# do not call this from other functions, might change session_id
# gets list of the sites per term
# and deletes them
def delete_all_sites_for_user(config, user_id, term_id):
	# getting all site list
	session_id = login_proxy.service.login(config['username'], config['password'])
	response = longsight_proxy.service.getSitesUserCanAccessFilteredByTerm(session_id, user_id, term_id)
	response_root = ET.fromstring(response)
	site_list = [each.text for each in response_root.iter('siteId')]

	#deleting the list of sites
	for site_id in site_list:
		deleted_site = script_proxy.service.removeSite(session_id, site_id)
		print(deleted_site)


def sakai_run(db_conn_params, config):
	#loging in to Sakai
	sakai_session = login_proxy.service.login(config['username'], config['password'])
	bs_term = int(config['bs_term'])
	with mysql.connector.connect(**db_conn_params) as conn:
		with conn.cursor(buffered=True) as cur:
			cur.execute(f"""select o.org_unit_id, o.name, o.is_active, o.code, s.site_id
							from org_units_descendants d
							left join tmp_org_units o
							on d.des_org_unit_id = o.org_unit_id
							left join sakai_sites s
							on d.des_org_unit_id = s.org_unit_id
							where d.org_unit_id = {bs_term} and o.org_unit_type_id = 3;""")
			course_offerings = cur.fetchall()

	for each in course_offerings:
		create_sakai_site(db_conn_params, each, config, sakai_session)

	print(len(course_offerings))

	drop_tmp_tables(db_conn_params)

	login_proxy.service.logout(sakai_session)

