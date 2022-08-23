CREATE TABLE users (
  user_id int(11) NOT NULL,
  user_name varchar(70) DEFAULT NULL,
  org_defined_id varchar(70) DEFAULT NULL,
  first_name varchar(70) DEFAULT NULL,
  middle_name varchar(70) DEFAULT NULL,
  last_name varchar(70) DEFAULT NULL,
  is_active varchar(20) DEFAULT NULL,
  organization varchar(255) DEFAULT NULL,
  external_email varchar(255) DEFAULT NULL,
  signup_date datetime DEFAULT NULL,
  first_login_date datetime DEFAULT NULL,
  version varchar(255) DEFAULT NULL,
  org_role_id int(11) DEFAULT NULL,
  PRIMARY KEY (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8