CREATE TABLE IF NOT EXISTS org_units (
  org_unit_id int(11) NOT NULL,
  organization varchar(255) DEFAULT NULL,
  type varchar(255) DEFAULT NULL,
  name text,
  code varchar(255) DEFAULT NULL,
  start_date datetime DEFAULT NULL,
  end_date datetime DEFAULT NULL,
  is_active varchar(6) DEFAULT NULL,
  created_date datetime DEFAULT NULL,
  is_deleted varchar(20) DEFAULT NULL,
  deleted_date datetime DEFAULT NULL,
  recycled_date datetime DEFAULT NULL,
  version varchar(255) DEFAULT NULL,
  org_unit_type_id int(11) DEFAULT NULL,
  PRIMARY KEY (org_unit_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8