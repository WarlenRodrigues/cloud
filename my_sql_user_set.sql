DROP USER IF EXISTS 'tasklist_app'@'localhost';
CREATE USER 'tasklist_app'@'localhost' IDENTIFIED BY "DBServer-EC2";
GRANT SELECT, INSERT, UPDATE, DELETE ON tasklist.* TO 'tasklist_app'@'localhost';