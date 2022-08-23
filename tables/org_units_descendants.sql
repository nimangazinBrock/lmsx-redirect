CREATE TABLE IF NOT EXISTS org_units_descendants (
  org_unit_id int(11) NOT NULL,
  des_org_unit_id int(11) NOT NULL,
  PRIMARY KEY (org_unit_id, des_org_unit_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8