/* 
to setup test tables: 
   sql tptest@tpdbmysql file tptrace_test_db.sql 
   sql tptest@tpdbmssql file tptrace_test_db.sql 
*/



DROP TABLE if exists orders;
CREATE TABLE orders (
   -- OrderId INT NOT NULL AUTO_INCREMENT,
   OrderId VARCHAR(20),
   Symbol VARCHAR(20),
   -- Sid INT(6),  -- this works in mysql but not in mssql
   Sid INT, 
   OrderQty INT,
   FilledQty INT,
   LastPrice DECIMAL(12,4),   -- don't use FLOAT because 'where Price = 135.35' not working
   LastQty INT, 
   AvgPrice DECIMAL(12,4), 
   SenderComp VARCHAR(10), 
   SenderSub VARCHAR(10), 
   TargetComp VARCHAR(10), 
   TargetSub VARCHAR(10), 
   CreateTime DATETIME,
   -- LastUpdateTime DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,--non-mssql
   LastUpdateTime DATETIME DEFAULT CURRENT_TIMESTAMP,
   TradeDate DATE, 
   -- PRIMARY KEY (`OrderId`) --non-mssql
   PRIMARY KEY (OrderId)
);
-- ALTER TABLE orders AUTO_INCREMENT=1000000;


