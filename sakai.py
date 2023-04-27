import mysql.connector
from zeep import Client
import uuid
from xml.etree import ElementTree as ET
import logging
import json
import datetime
from datetime import timedelta

CONFIG_LOCATION = 'bsp_config.json'
today = datetime.datetime.now()
yesterday = today - timedelta(days = 1)

with open(CONFIG_LOCATION, 'r') as f:
	config = json.load(f)

loginUrl = config["sakai_url"] + "/sakai-ws/soap/login?wsdl"
scriptUrl = config["sakai_url"] + "/sakai-ws/soap/sakai?wsdl"
longsightScriptUrl = config["sakai_url"] + "/sakai-ws/soap/longsight?wsdl"

login_proxy = Client(loginUrl)
script_proxy = Client(scriptUrl)
longsight_proxy = Client(longsightScriptUrl)

logging.basicConfig(filename = 'logging.log',
                    level = logging.WARNING,
                    format = '%(asctime)s:%(levelname)s:%(name)s:%(message)s')
 
# Create logger, set level, and add stream handler
parent_logger = logging.getLogger("parent")
parent_logger.setLevel(logging.INFO)
parent_shandler = logging.StreamHandler()
parent_logger.addHandler(parent_shandler)
 
logging.disable('DEBUG')


def generate_site_id():
	return uuid.uuid1()


def create_sakai_site(db_conn_params, params, config, session_id):
	
	if params[5]==None:
		start_date = yesterday
	else:
		start_date = params[5]

	if params[2] == 'False' or start_date>today:
		if params[4] != None:
			script_proxy.service.changeSitePublishStatus(session_id, params[4], False)
		else:
			return
	else:
		if params[4] != None:
			script_proxy.service.changeSitePublishStatus(session_id, params[4], True)
		else:
			new_site_id = generate_site_id()

			site_description = f"""<center><p><strong> {params[1]} is being offered in Brightspace this term!</strong> Use the button 
									on this page to continue to this course in Brightspace.</p>
									<p>&nbsp;</p>
									<p style='text-align:center'><button><span class='Mrphs-itemTitle'>
									<a href='https://brightspace.brocku.ca/d2l/home/{params[0]}' rel='noopener' target='_blank' 
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
			
			parent_logger.info(f"{params[1]} sakai site created")
			parent_logger.info(f"Running Sakai enrollments for {params[1]}")
			add_remove_users(db_conn_params, session_id, 1, new_site_id)


def add_sakai_site_to_DB(db_conn_params, org_unit_id, site_id):
	with mysql.connector.connect(**db_conn_params) as conn:
		with conn.cursor(buffered=True) as cur:
			cur.execute(f"""insert into sakai_sites (org_unit_id, site_id)
							values ({org_unit_id}, '{site_id}');""")
		conn.commit()

def add_remove_users(db_conn_params, session_id, delta = 0, sakai_site_id = "is not null"):
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
	
	if delta==0:
		enroll_table = "tmp_enroll_withdrawals"
	else:
		enroll_table = "enroll_withdrawals"
		sakai_site_id = f'= "{sakai_site_id}"'
	
	with mysql.connector.connect(**db_conn_params) as conn:
		with conn.cursor(buffered=True) as cur:
			cur.execute(f"""select u.user_name, e.action, e.role_id, s.site_id
						from {enroll_table} e
						left join users u
						on e.user_id = u.user_id
						left join sakai_sites s
						on e.org_unit_id = s.org_unit_id
						where s.site_id {sakai_site_id};""")
			all_enrollments = cur.fetchall()

			for user in all_enrollments:
				if not user:
					continue
				if user[1] == 'Enroll':
					try:
						script_proxy.service.addMemberToSiteWithRole(session_id, user[3], user[0], roles[user[2]])
					except:
						parent_logger.info(f"User not found!")
				else:
					script_proxy.service.removeMemberFromSite(session_id, user[3], user[0])


def drop_tmp_tables(db_conn_params):
	with mysql.connector.connect(**db_conn_params) as conn:
		with conn.cursor(buffered=True) as cur:
			cur.execute(f"show tables;")
			all_tables = cur.fetchall()

			for each in all_tables:
				if each[0].startswith('tmp'):
					cur.execute(f"drop table {each[0]};")
		conn.commit()


# do not call this from other functions, might change session_id
# gets list of the sites per term
# and deletes them
def delete_all_sites_for_user(config):
	# getting all site list
	session_id = login_proxy.service.login(config['username'], config['password'])
	response = longsight_proxy.service.getSitesUserCanAccessFilteredByTerm(session_id, config['username'], config['current_term_eid'])
	response_root = ET.fromstring(response)
	site_list = [each.text for each in response_root.iter('siteId')]

	#deleting the list of sites
	for site_id in site_list:
		deleted_site = script_proxy.service.removeSite(session_id, site_id)
		if deleted_site == 'success':
			parent_logger.info(f"Sakai site with {site_id} is deleted")


def sakai_run(db_conn_params, config, args):
	#loging in to Sakai
	sakai_session = login_proxy.service.login(config['username'], config['password'])
	bs_term = int(config['bs_term'])
	with mysql.connector.connect(**db_conn_params) as conn:
		with conn.cursor(buffered=True) as cur:
			cur.execute(f"""select o.org_unit_id, o.name, o.is_active, o.code, s.site_id, o.start_date, o.end_date
							from org_units_descendants d
							left join tmp_org_units o
							on d.des_org_unit_id = o.org_unit_id
							left join sakai_sites s
							on d.des_org_unit_id = s.org_unit_id
							where d.org_unit_id = {bs_term} and o.org_unit_type_id = 3;""")
			course_offerings = cur.fetchall()

	#create sakai sites
	for each in course_offerings:
		create_sakai_site(db_conn_params, each, config, sakai_session)

	total_offerings = len(course_offerings)
	parent_logger.info(f"{total_offerings} offerings are processed")
		
	#run delta enrollments
	if args.differential:
		parent_logger.info(f"Running Delta enrollments for Sakai")
		add_remove_users(db_conn_params, sakai_session)
	
	#drop diffential data tables
	drop_tmp_tables(db_conn_params)
	
	#log out Sakai
	login_proxy.service.logout(sakai_session)

