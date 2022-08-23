CREATE TABLE IF NOT EXISTS enroll_withdrawals (
  log_id int(11) NOT NULL,
  user_id int(11) NOT NULL,
  org_unit_id int(11) NOT NULL,
  role_id int(11) NOT NULL,
  action varchar(20) DEFAULT NULL,
  enrollment_type varchar(255) DEFAULT NULL,
  modified_by_user_id varchar(70) DEFAULT NULL,
  PRIMARY KEY (log_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8