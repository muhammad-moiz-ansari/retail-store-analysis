SYNTHETIC PURCHASE CONVERSION TEST DATA

Date range: 2004-12-21 through 2004-12-27 inclusive.
Timezone: +05:00. All prices are illustrative, not historical.

Import transactions.csv and footfall.csv. Import calendar.csv if supported.
Set the footfall import coverage fields using coverage_metadata.json:
coverage_from = 2004-12-21
coverage_to = 2004-12-27
complete = true
Apply this coverage to ENTRANCE-1 if coverage is configured per camera.
The JSON is a reference for the import settings; automatic JSON import support is unknown.

Expected results:
701 transaction line items; 350 distinct completed sale transactions.
1,000 in events and 1,000 out events. Only in events count.
Weekly conversion = 350 / 1000 = 0.35 = 35%.
All seven calendar days are open. No refunds or voids.

Date,Distinct sales,Entries,Conversion
2004-12-21,30,100,30.00%
2004-12-22,36,120,30.00%
2004-12-23,49,140,35.00%
2004-12-24,56,160,35.00%
2004-12-25,72,180,40.00%
2004-12-26,68,170,40.00%
2004-12-27,39,130,30.00%
