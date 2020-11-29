DROP DATABASE IF EXISTS tasklist;
CREATE DATABASE tasklist;

DROP TABLE IF EXISTS tasks;
CREATE TABLE tasks (
    id_task BINARY(16) PRIMARY KEY,
    description NVARCHAR(1024),
    completed BOOLEAN,
    id_user BINARY(16),
    FOREIGN KEY (id_user) REFERENCES users(id_user)
);

DROP TABLE IF EXISTS users;
CREATE TABLE users (
    id_user BINARY(16) PRIMARY KEY,
    username VARCHAR(50)
);
