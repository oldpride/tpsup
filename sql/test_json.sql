-- sql -attr LongReadLen=12800 tptest@tpdbmssql file test_json.sql

/* example is from
   https://docs.microsoft.com/en-us/sql/relational-databases/json/json-data-sql-server
*/
SELECT JSON_VALUE('{"info": {"address": [{"town": "Belgrade"}, {"town": "Paris"}, {"town":"Madrid"}]}}', '$.info.address[0].town') as FirstTown;

-- FirstTown
-- Belgrade

SELECT 'Really Is Json'
where ISJSON('{"info": {"address": [{"town": "Belgrade"}, {"town": "Paris"}, {"town":"Madrid"}]}}') > 0;

-- this query needs '-attr LongReadLen=12800'
/*
DECLARE @json NVARCHAR(MAX);
SET @json = '{"info": {"address": [{"town": "Belgrade"}, {"town": "Paris"}, {"town":"Madrid"}]}}';
SET @json = JSON_MODIFY(@json, '$.info.address[1].town', 'London');
SELECT modifiedJson = @json;
*/
SELECT JSON_MODIFY('{"info": {"address": [{"town": "Belgrade"}, {"town": "Paris"}, {"town":"Madrid"}]}}', '$.info.address[1].town', 'London');

