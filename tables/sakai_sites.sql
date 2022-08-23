CREATE TABLE sakai_sites (
  id int(11) NOT NULL AUTO_INCREMENT,
  org_unit_id int(20) NOT NULL,
  site_id varchar(40) DEFAULT NULL,
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8