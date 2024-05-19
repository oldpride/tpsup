#!/usr/bin/env python3

# from cookbook 3rd ed, page 214
# https://data.cityofchicago.org/Service-Requests/311-Service-Requests-Rodent-Baiting-Historical/97t6-zrhs
# redicted to https://data.cityofchicago.org/d/v6vf-nfxy
# downloaded the data in csv format

import pandas

# /home/tian/github/tpsup/python3/scripts/cookbook_panada.py:10: ParserWarning: Falling back to
# the 'python' engine because the 'c' engine does not support skipfooter; you can avoid this
# warning by specifying engine='python'.
# rats = pandas.read_csv('/home/tian/data/panda/311_service_requests.csv', skipfooter=1)

rats = pandas.read_csv('/home/tian/data/panda/311_service_requests.csv', engine='python', skipfooter=1)

# the above load csv file to create a Pandas Dataframe
# https://www.shanelynn.ie/using-pandas-dataframe-creating-editing-viewing-data-in-python/

# print the dataframe description
print(rats)
#              SR_NUMBER                                        SR_TYPE  ... Census Tracts Wards
# 0        SR19-01924579                       Aircraft Noise Complaint  ...           NaN   NaN
# 1        SR19-01924576                           Weed Removal Request  ...         280.0   3.0
# 2        SR19-01924574                       Aircraft Noise Complaint  ...           NaN   NaN
# 3        SR19-01924573                      311 INFORMATION ONLY CALL  ...           NaN   NaN
# 4        SR19-01924572                       Garbage Cart Maintenance  ...         286.0  49.0
# ...                ...                                            ...  ...           ...   ...
# 1287250  SR18-00011714              Sewer Cleaning Inspection Request  ...         454.0  49.0
# 1287251  SR18-00011711                             Building Violation  ...          54.0  24.0
# 1287252  SR18-00011710                             Building Violation  ...         123.0  48.0
# 1287253  SR18-00011708  No Building Permit and Construction Violation  ...         360.0  50.0
# 1287254  SR18-00011706                             Building Violation  ...         652.0  36.0
# 
# [1287255 rows x 42 columns]

#print the dataframe shape
print(rats.shape)
# (1287255, 42)

# print the dataframe dimension
print(rats.ndim)
# 2

#>>> print(rats.head())
#       SR_NUMBER                    SR_TYPE SR_SHORT_CODE  ... Zip Codes Census Tracts Wards
#0  SR19-01924579   Aircraft Noise Complaint           AVN  ...       NaN           NaN   NaN
#1  SR19-01924576       Weed Removal Request           SCP  ...   22257.0         280.0   3.0
#2  SR19-01924574   Aircraft Noise Complaint           AVN  ...       NaN           NaN   NaN
#3  SR19-01924573  311 INFORMATION ONLY CALL        311IOC  ...       NaN           NaN   NaN
#4  SR19-01924572   Garbage Cart Maintenance           SIE  ...    4299.0         286.0  49.0
#
#[5 rows x 42 columns]
#>>> print(rats.tail())
#             SR_NUMBER                                        SR_TYPE  ... Census Tracts Wards
#1287250  SR18-00011714              Sewer Cleaning Inspection Request  ...         454.0  49.0
#1287251  SR18-00011711                             Building Violation  ...          54.0  24.0
#1287252  SR18-00011710                             Building Violation  ...         123.0  48.0
#1287253  SR18-00011708  No Building Permit and Construction Violation  ...         360.0  50.0
#1287254  SR18-00011706                             Building Violation  ...         652.0  36.0
#
#[5 rows x 42 columns]
#
#There are three main methods of selecting columns in pandas:
#   using a dot notation, e.g. data.column_name,
#   using square braces and the name of the column as a string, e.g. data['column_name']
#   or using numeric indexing and the iloc selector data.iloc[:, <column_number>]
#
#
#>>> print(rats.dtypes())
#Traceback (most recent call last):
#  File "<stdin>", line 1, in <module>
#TypeError: 'Series' object is not callable
#>>> print(rats.dtypes)
#SR_NUMBER                    object
#SR_TYPE                      object
#SR_SHORT_CODE                object
#OWNER_DEPARTMENT             object
#STATUS                       object
#CREATED_DATE                 object
#LAST_MODIFIED_DATE           object
#CLOSED_DATE                  object
#STREET_ADDRESS               object
#CITY                         object
#STATE                        object
#...
#DUPLICATE                      bool
#...
#
#Note that strings are loaded as ‘object’ datatypes, because technically, the DataFrame holds a pointer to the string data elsewhere in memory. This behaviour is expected, and can be ignored.
#
# to change datatype from bool to int32
# rats.astype({'DUPLICATE': 'int32'}).dtypes
#...
#DUPLICATE                     int32
#...
#
#note:
#we cannot convert 'object' type to 'str'
#https://stackoverflow.com/questions/33957720/how-to-convert-column-with-dtype-as-object-to-string-in-pandas-dataframe
## so this won't work
#rats.astype({'SR_NUMBER': 'str'}).dtypes
#
#>>> rats.describe()
#       COMMUNITY_AREA          WARD  ELECTRICAL_DISTRICT  ...     Zip Codes  Census Tracts         Wards
#count    1.263840e+06  1.263882e+06        694149.000000  ...  1.264374e+06   1.262971e+06  1.262869e+06
#mean     3.826350e+01  2.666563e+01             7.426038  ...  1.932731e+04   3.399521e+02  2.574445e+01
#std      2.256416e+01  1.243390e+01             3.891117  ...  5.089855e+03   2.708225e+02  1.231375e+01
#min      1.000000e+00  1.000000e+00             1.000000  ...  2.733000e+03   1.000000e+00  1.000000e+00
#25%      2.400000e+01  1.800000e+01             4.000000  ...  2.118400e+04   4.900000e+01  1.900000e+01
#50%      2.800000e+01  2.800000e+01             7.000000  ...  2.120200e+04   3.240000e+02  2.300000e+01
#75%      6.000000e+01  3.700000e+01            11.000000  ...  2.186900e+04   6.090000e+02  3.400000e+01
#max      7.700000e+01  5.000000e+01            15.000000  ...  2.691200e+04   8.010000e+02  5.000000e+01
#
#[8 rows x 19 columns]
#
#>>> rats['Census Tracts'].describe()
#count    1.262971e+06
#mean     3.399521e+02
#std      2.708225e+02
#min      1.000000e+00
#25%      4.900000e+01
#50%      3.240000e+02
#75%      6.090000e+02
#max      8.010000e+02
#Name: Census Tracts, dtype: float64
#
#>>> rats['Census Tracts'].max()
#801.0
#
#drop columns
#>>> rats2 = rats.drop(['CITY','STATE'], axis=1)
#>>> rats2 = rats.drop(columns=['CITY','STATE'])
#in-place
#>>> rats.drop(columns=['CITY','STATE'], inplace=True)
#>>> rats.dtypes
#(CITY,STATE are gone)
#
## Delete the rows with labels 0,1,2
#data = data.drop([0,1,2], axis=0)
#
## Delete the rows with label "Ireland"
## For label-based deletion, set the index first on the dataframe:
#data = data.set_index("Area")
#data = data.drop("Ireland", axis=0). # Delete all rows with label "Ireland"
#
## Delete the first five rows using iloc selector
#data = data.iloc[5:,]
#
## Output data to a CSV file
## Typically, I don't want row numbers in my output file, hence index=False.
## To avoid character issues, I typically use utf8 encoding for input/output.
#>>> rats.to_csv("/tmp/junk.csv", index=False, encoding='utf8')
#
## Output data to an Excel file.
## For the excel output to work, you need to install the "xlsxwriter" package.
#rats=rats.iloc[:4,] # first drop most lines so that the file won't go over limit
#rats.to_excel("/tmp/junk.xlsx", sheet_name="Sheet 1", index=False)
#
