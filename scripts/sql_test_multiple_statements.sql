/* 
   this is a multi-line comment
*/

DROP TABLE if exists orders;

-- this is single-line comment 1
CREATE TABLE orders (
   Id INT NOT NULL AUTO_INCREMENT,
   OrderId VARCHAR(20),
   -- this is single-line comment 2
   PRIMARY KEY (`Id`)
);

