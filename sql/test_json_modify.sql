-- sql -attr LongReadLen=12800 -NotSplitAtSemiColon tptest@tpdbmssql file test_json_modify.sql

DECLARE @json NVARCHAR(MAX);
SET @json = '{"info": {"address": [{"town": "Belgrade"}, {"town": "Paris"}, {"town":"Madrid"}]}}';
SET @json = JSON_MODIFY(@json, '$.info.address[1].town', 'London');
SELECT modifiedJson = @json;

GO;

-- sql -attr LongReadLen=12800 tptest@tpdbmssql file test_json_modify.sql
SELECT JSON_MODIFY('{"info": {"address": [{"town": "Belgrade"}, {"town": "Paris"}, {"town":"Madrid"}]}}', '$.info.address[1].town', 'London');
