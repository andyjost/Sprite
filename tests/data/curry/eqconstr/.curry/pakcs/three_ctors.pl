%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(three_ctors).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('three_ctors.goal200',goal200,0,'three_ctors.goal200',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal201',goal201,0,'three_ctors.goal201',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal202',goal202,0,'three_ctors.goal202',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal203',goal203,0,'three_ctors.goal203',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal204',goal204,0,'three_ctors.goal204',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal205',goal205,0,'three_ctors.goal205',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal206',goal206,0,'three_ctors.goal206',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal207',goal207,0,'three_ctors.goal207',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal208',goal208,0,'three_ctors.goal208',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal209',goal209,0,'three_ctors.goal209',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal210',goal210,0,'three_ctors.goal210',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal211',goal211,0,'three_ctors.goal211',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal212',goal212,0,'three_ctors.goal212',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal213',goal213,0,'three_ctors.goal213',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal214',goal214,0,'three_ctors.goal214',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal215',goal215,0,'three_ctors.goal215',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal216',goal216,0,'three_ctors.goal216',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal217',goal217,0,'three_ctors.goal217',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal218',goal218,0,'three_ctors.goal218',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal219',goal219,0,'three_ctors.goal219',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal304',goal304,0,'three_ctors.goal304',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal305',goal305,0,'three_ctors.goal305',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal306',goal306,0,'three_ctors.goal306',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal307',goal307,0,'three_ctors.goal307',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal308',goal308,0,'three_ctors.goal308',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal309',goal309,0,'three_ctors.goal309',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal310',goal310,0,'three_ctors.goal310',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal311',goal311,0,'three_ctors.goal311',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal312',goal312,0,'three_ctors.goal312',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal313',goal313,0,'three_ctors.goal313',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal314',goal314,0,'three_ctors.goal314',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal315',goal315,0,'three_ctors.goal315',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal316',goal316,0,'three_ctors.goal316',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal317',goal317,0,'three_ctors.goal317',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal318',goal318,0,'three_ctors.goal318',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal319',goal319,0,'three_ctors.goal319',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal404',goal404,0,'three_ctors.goal404',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal405',goal405,0,'three_ctors.goal405',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal406',goal406,0,'three_ctors.goal406',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal407',goal407,0,'three_ctors.goal407',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal408',goal408,0,'three_ctors.goal408',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal409',goal409,0,'three_ctors.goal409',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal410',goal410,0,'three_ctors.goal410',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal411',goal411,0,'three_ctors.goal411',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal412',goal412,0,'three_ctors.goal412',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal413',goal413,0,'three_ctors.goal413',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal414',goal414,0,'three_ctors.goal414',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal415',goal415,0,'three_ctors.goal415',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal416',goal416,0,'three_ctors.goal416',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal417',goal417,0,'three_ctors.goal417',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal418',goal418,0,'three_ctors.goal418',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal419',goal419,0,'three_ctors.goal419',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal504',goal504,0,'three_ctors.goal504',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal505',goal505,0,'three_ctors.goal505',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal506',goal506,0,'three_ctors.goal506',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal507',goal507,0,'three_ctors.goal507',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal508',goal508,0,'three_ctors.goal508',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal509',goal509,0,'three_ctors.goal509',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal510',goal510,0,'three_ctors.goal510',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal511',goal511,0,'three_ctors.goal511',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal512',goal512,0,'three_ctors.goal512',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal513',goal513,0,'three_ctors.goal513',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal514',goal514,0,'three_ctors.goal514',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal515',goal515,0,'three_ctors.goal515',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal516',goal516,0,'three_ctors.goal516',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal517',goal517,0,'three_ctors.goal517',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal518',goal518,0,'three_ctors.goal518',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal519',goal519,0,'three_ctors.goal519',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal604',goal604,0,'three_ctors.goal604',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal605',goal605,0,'three_ctors.goal605',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal606',goal606,0,'three_ctors.goal606',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal607',goal607,0,'three_ctors.goal607',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal608',goal608,0,'three_ctors.goal608',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal609',goal609,0,'three_ctors.goal609',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal610',goal610,0,'three_ctors.goal610',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal611',goal611,0,'three_ctors.goal611',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal612',goal612,0,'three_ctors.goal612',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal613',goal613,0,'three_ctors.goal613',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal614',goal614,0,'three_ctors.goal614',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal615',goal615,0,'three_ctors.goal615',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal616',goal616,0,'three_ctors.goal616',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal617',goal617,0,'three_ctors.goal617',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal618',goal618,0,'three_ctors.goal618',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal619',goal619,0,'three_ctors.goal619',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal704',goal704,0,'three_ctors.goal704',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal705',goal705,0,'three_ctors.goal705',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal706',goal706,0,'three_ctors.goal706',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal707',goal707,0,'three_ctors.goal707',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal708',goal708,0,'three_ctors.goal708',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal709',goal709,0,'three_ctors.goal709',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal710',goal710,0,'three_ctors.goal710',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal711',goal711,0,'three_ctors.goal711',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal712',goal712,0,'three_ctors.goal712',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal713',goal713,0,'three_ctors.goal713',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal714',goal714,0,'three_ctors.goal714',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal715',goal715,0,'three_ctors.goal715',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal716',goal716,0,'three_ctors.goal716',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal717',goal717,0,'three_ctors.goal717',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal718',goal718,0,'three_ctors.goal718',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal719',goal719,0,'three_ctors.goal719',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal804',goal804,0,'three_ctors.goal804',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal805',goal805,0,'three_ctors.goal805',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal806',goal806,0,'three_ctors.goal806',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal807',goal807,0,'three_ctors.goal807',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal808',goal808,0,'three_ctors.goal808',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal809',goal809,0,'three_ctors.goal809',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal810',goal810,0,'three_ctors.goal810',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal811',goal811,0,'three_ctors.goal811',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal812',goal812,0,'three_ctors.goal812',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal813',goal813,0,'three_ctors.goal813',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal814',goal814,0,'three_ctors.goal814',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal815',goal815,0,'three_ctors.goal815',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal816',goal816,0,'three_ctors.goal816',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal817',goal817,0,'three_ctors.goal817',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal818',goal818,0,'three_ctors.goal818',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal819',goal819,0,'three_ctors.goal819',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal904',goal904,0,'three_ctors.goal904',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal905',goal905,0,'three_ctors.goal905',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal906',goal906,0,'three_ctors.goal906',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal907',goal907,0,'three_ctors.goal907',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal908',goal908,0,'three_ctors.goal908',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal909',goal909,0,'three_ctors.goal909',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal910',goal910,0,'three_ctors.goal910',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal911',goal911,0,'three_ctors.goal911',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal912',goal912,0,'three_ctors.goal912',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal913',goal913,0,'three_ctors.goal913',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal914',goal914,0,'three_ctors.goal914',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal915',goal915,0,'three_ctors.goal915',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal916',goal916,0,'three_ctors.goal916',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal917',goal917,0,'three_ctors.goal917',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal918',goal918,0,'three_ctors.goal918',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal919',goal919,0,'three_ctors.goal919',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal1004',goal1004,0,'three_ctors.goal1004',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal1005',goal1005,0,'three_ctors.goal1005',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal1006',goal1006,0,'three_ctors.goal1006',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal1007',goal1007,0,'three_ctors.goal1007',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal1008',goal1008,0,'three_ctors.goal1008',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal1009',goal1009,0,'three_ctors.goal1009',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal1010',goal1010,0,'three_ctors.goal1010',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal1011',goal1011,0,'three_ctors.goal1011',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal1012',goal1012,0,'three_ctors.goal1012',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal1013',goal1013,0,'three_ctors.goal1013',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal1014',goal1014,0,'three_ctors.goal1014',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal1015',goal1015,0,'three_ctors.goal1015',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal1016',goal1016,0,'three_ctors.goal1016',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal1017',goal1017,0,'three_ctors.goal1017',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal1018',goal1018,0,'three_ctors.goal1018',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal1019',goal1019,0,'three_ctors.goal1019',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal1104',goal1104,0,'three_ctors.goal1104',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal1105',goal1105,0,'three_ctors.goal1105',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal1106',goal1106,0,'three_ctors.goal1106',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal1107',goal1107,0,'three_ctors.goal1107',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal1108',goal1108,0,'three_ctors.goal1108',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal1109',goal1109,0,'three_ctors.goal1109',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal1110',goal1110,0,'three_ctors.goal1110',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal1111',goal1111,0,'three_ctors.goal1111',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal1112',goal1112,0,'three_ctors.goal1112',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal1113',goal1113,0,'three_ctors.goal1113',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal1114',goal1114,0,'three_ctors.goal1114',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal1115',goal1115,0,'three_ctors.goal1115',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal1116',goal1116,0,'three_ctors.goal1116',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal1117',goal1117,0,'three_ctors.goal1117',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal1118',goal1118,0,'three_ctors.goal1118',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal1119',goal1119,0,'three_ctors.goal1119',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal1204',goal1204,0,'three_ctors.goal1204',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal1205',goal1205,0,'three_ctors.goal1205',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal1206',goal1206,0,'three_ctors.goal1206',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal1207',goal1207,0,'three_ctors.goal1207',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal1208',goal1208,0,'three_ctors.goal1208',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal1209',goal1209,0,'three_ctors.goal1209',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal1210',goal1210,0,'three_ctors.goal1210',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal1211',goal1211,0,'three_ctors.goal1211',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal1212',goal1212,0,'three_ctors.goal1212',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal1213',goal1213,0,'three_ctors.goal1213',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal1214',goal1214,0,'three_ctors.goal1214',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal1215',goal1215,0,'three_ctors.goal1215',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal1216',goal1216,0,'three_ctors.goal1216',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal1217',goal1217,0,'three_ctors.goal1217',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal1218',goal1218,0,'three_ctors.goal1218',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal1219',goal1219,0,'three_ctors.goal1219',nofix,'TCons'('three_ctors.Z',[])).
functiontype('three_ctors.goal1',goal1,0,'three_ctors.goal1',nofix,'TCons'('three_ctors.ABC',[])).
functiontype('three_ctors.goal2',goal2,0,'three_ctors.goal2',nofix,'TCons'('three_ctors.ABC',[])).
functiontype('three_ctors.goal3',goal3,0,'three_ctors.goal3',nofix,'TCons'('three_ctors.ABC',[])).
functiontype('three_ctors.goal4',goal4,0,'three_ctors.goal4',nofix,'TCons'('three_ctors.ABC',[])).
functiontype('three_ctors.goal5',goal5,0,'three_ctors.goal5',nofix,'TCons'('three_ctors.ABC',[])).
functiontype('three_ctors.goal6',goal6,0,'three_ctors.goal6',nofix,'TCons'('three_ctors.ABC',[])).
functiontype('three_ctors.goal7',goal7,0,'three_ctors.goal7',nofix,'TCons'('three_ctors.ABC',[])).
functiontype('three_ctors.goal8',goal8,0,'three_ctors.goal8',nofix,'TCons'('three_ctors.ABC',[])).
functiontype('three_ctors.goal9',goal9,0,'three_ctors.goal9',nofix,'TCons'('three_ctors.ABC',[])).
functiontype('three_ctors.goal10',goal10,0,'three_ctors.goal10',nofix,'TCons'('three_ctors.ABC',[])).
functiontype('three_ctors.goal11',goal11,0,'three_ctors.goal11',nofix,'TCons'('three_ctors.ABC',[])).
functiontype('three_ctors.goal12',goal12,0,'three_ctors.goal12',nofix,'TCons'('three_ctors.ABC',[])).
functiontype('three_ctors.goal101',goal101,0,'three_ctors.goal101',nofix,'TCons'('three_ctors.ABC',[])).
functiontype('three_ctors.goal102',goal102,0,'three_ctors.goal102',nofix,'TCons'('three_ctors.ABC',[])).
functiontype('three_ctors.goal103',goal103,0,'three_ctors.goal103',nofix,'TCons'('three_ctors.ABC',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.
constructortype('three_ctors.Z','Z',0,'Z',0,'TCons'('three_ctors.Z',[]),[]).
constructortype('three_ctors.A','A',0,'A',0,'TCons'('three_ctors.ABC',[]),['three_ctors.B'/0,'three_ctors.C'/0]).
constructortype('three_ctors.B','B',0,'B',1,'TCons'('three_ctors.ABC',[]),['three_ctors.A'/0,'three_ctors.C'/0]).
constructortype('three_ctors.C','C',0,'C',2,'TCons'('three_ctors.ABC',[]),['three_ctors.A'/0,'three_ctors.B'/0]).

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'three_ctors.goal200'(_G685420,_G685421,_G685422):-freeze(_G685421,'blocked_three_ctors.goal200'(_G685420,_G685421,_G685422)).
'blocked_three_ctors.goal200'(_G685619,_G685622,_G685625):-makeShare(_G685456,_G685651),hnf('Prelude.&>'('Prelude.=:='(_G685651,'three_ctors.Z'),_G685651),_G685619,_G685622,_G685625).

'three_ctors.goal201'(_G686654,_G686655,_G686656):-freeze(_G686655,'blocked_three_ctors.goal201'(_G686654,_G686655,_G686656)).
'blocked_three_ctors.goal201'(_G686853,_G686856,_G686859):-makeShare(_G686690,_G686885),hnf('Prelude.&>'('Prelude.=:='('three_ctors.Z',_G686885),_G686885),_G686853,_G686856,_G686859).

'three_ctors.goal202'(_G687888,_G687889,_G687890):-freeze(_G687889,'blocked_three_ctors.goal202'(_G687888,_G687889,_G687890)).
'blocked_three_ctors.goal202'(_G688160,_G688163,_G688166):-makeShare(_G687924,_G688198),hnf('Prelude.?'('Prelude.&>'('Prelude.=:='(_G688198,'three_ctors.Z'),_G688198),_G688198),_G688160,_G688163,_G688166).

'three_ctors.goal203'(_G689333,_G689334,_G689335):-freeze(_G689334,'blocked_three_ctors.goal203'(_G689333,_G689334,_G689335)).
'blocked_three_ctors.goal203'(_G689605,_G689608,_G689611):-makeShare(_G689369,_G689643),hnf('Prelude.?'('Prelude.&>'('Prelude.=:='('three_ctors.Z',_G689643),_G689643),_G689643),_G689605,_G689608,_G689611).

'three_ctors.goal204'(_G690778,_G690779,_G690780):-freeze(_G690779,'blocked_three_ctors.goal204'(_G690778,_G690779,_G690780)).
'blocked_three_ctors.goal204'(_G691135,_G691138,_G691141):-makeShare(_G690814,_G691191),makeShare(_G690823,_G691201),hnf('Prelude.&>'('Prelude.&'('Prelude.=:='(_G691191,_G691201),'Prelude.=:='(_G691201,'three_ctors.Z')),_G691191),_G691135,_G691138,_G691141).

'three_ctors.goal205'(_G692630,_G692631,_G692632):-freeze(_G692631,'blocked_three_ctors.goal205'(_G692630,_G692631,_G692632)).
'blocked_three_ctors.goal205'(_G692987,_G692990,_G692993):-makeShare(_G692675,_G693049),hnf('Prelude.&>'('Prelude.&'('Prelude.=:='(_G692666,_G693049),'Prelude.=:='(_G693049,'three_ctors.Z')),_G693049),_G692987,_G692990,_G692993).

'three_ctors.goal206'(_G694375,_G694376,_G694377):-freeze(_G694376,'blocked_three_ctors.goal206'(_G694375,_G694376,_G694377)).
'blocked_three_ctors.goal206'(_G694732,_G694735,_G694738):-makeShare(_G694411,_G694788),makeShare(_G694420,_G694798),hnf('Prelude.&>'('Prelude.&'('Prelude.=:='(_G694788,_G694798),'Prelude.=:='('three_ctors.Z',_G694798)),_G694788),_G694732,_G694735,_G694738).

'three_ctors.goal207'(_G696227,_G696228,_G696229):-freeze(_G696228,'blocked_three_ctors.goal207'(_G696227,_G696228,_G696229)).
'blocked_three_ctors.goal207'(_G696584,_G696587,_G696590):-makeShare(_G696272,_G696646),hnf('Prelude.&>'('Prelude.&'('Prelude.=:='(_G696263,_G696646),'Prelude.=:='('three_ctors.Z',_G696646)),_G696646),_G696584,_G696587,_G696590).

'three_ctors.goal208'(_G697972,_G697973,_G697974):-freeze(_G697973,'blocked_three_ctors.goal208'(_G697972,_G697973,_G697974)).
'blocked_three_ctors.goal208'(_G698329,_G698332,_G698335):-makeShare(_G698017,_G698385),makeShare(_G698008,_G698395),hnf('Prelude.&>'('Prelude.&'('Prelude.=:='(_G698385,_G698395),'Prelude.=:='(_G698385,'three_ctors.Z')),_G698395),_G698329,_G698332,_G698335).

'three_ctors.goal209'(_G699824,_G699825,_G699826):-freeze(_G699825,'blocked_three_ctors.goal209'(_G699824,_G699825,_G699826)).
'blocked_three_ctors.goal209'(_G700181,_G700184,_G700187):-makeShare(_G699869,_G700231),hnf('Prelude.&>'('Prelude.&'('Prelude.=:='(_G700231,_G699860),'Prelude.=:='(_G700231,'three_ctors.Z')),_G700231),_G700181,_G700184,_G700187).

'three_ctors.goal210'(_G701557,_G701558,_G701559):-freeze(_G701558,'blocked_three_ctors.goal210'(_G701557,_G701558,_G701559)).
'blocked_three_ctors.goal210'(_G701914,_G701917,_G701920):-makeShare(_G701602,_G701970),makeShare(_G701593,_G701980),hnf('Prelude.&>'('Prelude.&'('Prelude.=:='(_G701970,_G701980),'Prelude.=:='('three_ctors.Z',_G701970)),_G701980),_G701914,_G701917,_G701920).

'three_ctors.goal211'(_G703409,_G703410,_G703411):-freeze(_G703410,'blocked_three_ctors.goal211'(_G703409,_G703410,_G703411)).
'blocked_three_ctors.goal211'(_G703766,_G703769,_G703772):-makeShare(_G703454,_G703816),hnf('Prelude.&>'('Prelude.&'('Prelude.=:='(_G703816,_G703445),'Prelude.=:='('three_ctors.Z',_G703816)),_G703816),_G703766,_G703769,_G703772).

'three_ctors.goal212'(_G705142,_G705143,_G705144):-freeze(_G705143,'blocked_three_ctors.goal212'(_G705142,_G705143,_G705144)).
'blocked_three_ctors.goal212'(_G705499,_G705502,_G705505):-makeShare(_G705187,_G705555),makeShare(_G705178,_G705565),hnf('Prelude.&>'('Prelude.&'('Prelude.=:='(_G705555,'three_ctors.Z'),'Prelude.=:='(_G705565,_G705555)),_G705565),_G705499,_G705502,_G705505).

'three_ctors.goal213'(_G706994,_G706995,_G706996):-freeze(_G706995,'blocked_three_ctors.goal213'(_G706994,_G706995,_G706996)).
'blocked_three_ctors.goal213'(_G707351,_G707354,_G707357):-makeShare(_G707039,_G707401),hnf('Prelude.&>'('Prelude.&'('Prelude.=:='(_G707401,'three_ctors.Z'),'Prelude.=:='(_G707030,_G707401)),_G707401),_G707351,_G707354,_G707357).

'three_ctors.goal214'(_G708727,_G708728,_G708729):-freeze(_G708728,'blocked_three_ctors.goal214'(_G708727,_G708728,_G708729)).
'blocked_three_ctors.goal214'(_G709084,_G709087,_G709090):-makeShare(_G708772,_G709140),makeShare(_G708763,_G709150),hnf('Prelude.&>'('Prelude.&'('Prelude.=:='('three_ctors.Z',_G709140),'Prelude.=:='(_G709150,_G709140)),_G709150),_G709084,_G709087,_G709090).

'three_ctors.goal215'(_G710579,_G710580,_G710581):-freeze(_G710580,'blocked_three_ctors.goal215'(_G710579,_G710580,_G710581)).
'blocked_three_ctors.goal215'(_G710936,_G710939,_G710942):-makeShare(_G710624,_G710986),hnf('Prelude.&>'('Prelude.&'('Prelude.=:='('three_ctors.Z',_G710986),'Prelude.=:='(_G710615,_G710986)),_G710986),_G710936,_G710939,_G710942).

'three_ctors.goal216'(_G712312,_G712313,_G712314):-freeze(_G712313,'blocked_three_ctors.goal216'(_G712312,_G712313,_G712314)).
'blocked_three_ctors.goal216'(_G712669,_G712672,_G712675):-makeShare(_G712357,_G712725),makeShare(_G712348,_G712735),hnf('Prelude.&>'('Prelude.&'('Prelude.=:='(_G712725,'three_ctors.Z'),'Prelude.=:='(_G712725,_G712735)),_G712735),_G712669,_G712672,_G712675).

'three_ctors.goal217'(_G714164,_G714165,_G714166):-freeze(_G714165,'blocked_three_ctors.goal217'(_G714164,_G714165,_G714166)).
'blocked_three_ctors.goal217'(_G714521,_G714524,_G714527):-makeShare(_G714209,_G714571),hnf('Prelude.&>'('Prelude.&'('Prelude.=:='(_G714571,'three_ctors.Z'),'Prelude.=:='(_G714571,_G714200)),_G714571),_G714521,_G714524,_G714527).

'three_ctors.goal218'(_G715897,_G715898,_G715899):-freeze(_G715898,'blocked_three_ctors.goal218'(_G715897,_G715898,_G715899)).
'blocked_three_ctors.goal218'(_G716254,_G716257,_G716260):-makeShare(_G715942,_G716310),makeShare(_G715933,_G716320),hnf('Prelude.&>'('Prelude.&'('Prelude.=:='('three_ctors.Z',_G716310),'Prelude.=:='(_G716310,_G716320)),_G716320),_G716254,_G716257,_G716260).

'three_ctors.goal219'(_G717749,_G717750,_G717751):-freeze(_G717750,'blocked_three_ctors.goal219'(_G717749,_G717750,_G717751)).
'blocked_three_ctors.goal219'(_G718106,_G718109,_G718112):-makeShare(_G717794,_G718156),hnf('Prelude.&>'('Prelude.&'('Prelude.=:='('three_ctors.Z',_G718156),'Prelude.=:='(_G718156,_G717785)),_G718156),_G718106,_G718109,_G718112).

'three_ctors.goal304'(_G719482,_G719483,_G719484):-freeze(_G719483,'blocked_three_ctors.goal304'(_G719482,_G719483,_G719484)).
'blocked_three_ctors.goal304'(_G719912,_G719915,_G719918):-makeShare(_G719518,_G719974),makeShare(_G719527,_G719984),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G719974,_G719984),'Prelude.=:='(_G719984,'three_ctors.Z')),_G719974),_G719974),_G719912,_G719915,_G719918).

'three_ctors.goal305'(_G721545,_G721546,_G721547):-freeze(_G721546,'blocked_three_ctors.goal305'(_G721545,_G721546,_G721547)).
'blocked_three_ctors.goal305'(_G721975,_G721978,_G721981):-makeShare(_G721581,_G722043),makeShare(_G721590,_G722053),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G722043,_G722053),'Prelude.=:='(_G722053,'three_ctors.Z')),_G722053),_G722043),_G721975,_G721978,_G721981).

'three_ctors.goal306'(_G723614,_G723615,_G723616):-freeze(_G723615,'blocked_three_ctors.goal306'(_G723614,_G723615,_G723616)).
'blocked_three_ctors.goal306'(_G724044,_G724047,_G724050):-makeShare(_G723650,_G724106),makeShare(_G723659,_G724116),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G724106,_G724116),'Prelude.=:='('three_ctors.Z',_G724116)),_G724106),_G724106),_G724044,_G724047,_G724050).

'three_ctors.goal307'(_G725677,_G725678,_G725679):-freeze(_G725678,'blocked_three_ctors.goal307'(_G725677,_G725678,_G725679)).
'blocked_three_ctors.goal307'(_G726107,_G726110,_G726113):-makeShare(_G725713,_G726175),makeShare(_G725722,_G726185),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G726175,_G726185),'Prelude.=:='('three_ctors.Z',_G726185)),_G726185),_G726175),_G726107,_G726110,_G726113).

'three_ctors.goal308'(_G727746,_G727747,_G727748):-freeze(_G727747,'blocked_three_ctors.goal308'(_G727746,_G727747,_G727748)).
'blocked_three_ctors.goal308'(_G728176,_G728179,_G728182):-makeShare(_G727791,_G728244),makeShare(_G727782,_G728254),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G728244,_G728254),'Prelude.=:='(_G728244,'three_ctors.Z')),_G728254),_G728254),_G728176,_G728179,_G728182).

'three_ctors.goal309'(_G729815,_G729816,_G729817):-freeze(_G729816,'blocked_three_ctors.goal309'(_G729815,_G729816,_G729817)).
'blocked_three_ctors.goal309'(_G730245,_G730248,_G730251):-makeShare(_G729860,_G730307),makeShare(_G729851,_G730317),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G730307,_G730317),'Prelude.=:='(_G730307,'three_ctors.Z')),_G730307),_G730317),_G730245,_G730248,_G730251).

'three_ctors.goal310'(_G731878,_G731879,_G731880):-freeze(_G731879,'blocked_three_ctors.goal310'(_G731878,_G731879,_G731880)).
'blocked_three_ctors.goal310'(_G732308,_G732311,_G732314):-makeShare(_G731923,_G732376),makeShare(_G731914,_G732386),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G732376,_G732386),'Prelude.=:='('three_ctors.Z',_G732376)),_G732386),_G732386),_G732308,_G732311,_G732314).

'three_ctors.goal311'(_G733947,_G733948,_G733949):-freeze(_G733948,'blocked_three_ctors.goal311'(_G733947,_G733948,_G733949)).
'blocked_three_ctors.goal311'(_G734377,_G734380,_G734383):-makeShare(_G733992,_G734439),makeShare(_G733983,_G734449),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G734439,_G734449),'Prelude.=:='('three_ctors.Z',_G734439)),_G734439),_G734449),_G734377,_G734380,_G734383).

'three_ctors.goal312'(_G736010,_G736011,_G736012):-freeze(_G736011,'blocked_three_ctors.goal312'(_G736010,_G736011,_G736012)).
'blocked_three_ctors.goal312'(_G736440,_G736443,_G736446):-makeShare(_G736055,_G736508),makeShare(_G736046,_G736518),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G736508,'three_ctors.Z'),'Prelude.=:='(_G736518,_G736508)),_G736518),_G736518),_G736440,_G736443,_G736446).

'three_ctors.goal313'(_G738079,_G738080,_G738081):-freeze(_G738080,'blocked_three_ctors.goal313'(_G738079,_G738080,_G738081)).
'blocked_three_ctors.goal313'(_G738509,_G738512,_G738515):-makeShare(_G738124,_G738571),makeShare(_G738115,_G738581),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G738571,'three_ctors.Z'),'Prelude.=:='(_G738581,_G738571)),_G738571),_G738581),_G738509,_G738512,_G738515).

'three_ctors.goal314'(_G740142,_G740143,_G740144):-freeze(_G740143,'blocked_three_ctors.goal314'(_G740142,_G740143,_G740144)).
'blocked_three_ctors.goal314'(_G740572,_G740575,_G740578):-makeShare(_G740187,_G740640),makeShare(_G740178,_G740650),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='('three_ctors.Z',_G740640),'Prelude.=:='(_G740650,_G740640)),_G740650),_G740650),_G740572,_G740575,_G740578).

'three_ctors.goal315'(_G742211,_G742212,_G742213):-freeze(_G742212,'blocked_three_ctors.goal315'(_G742211,_G742212,_G742213)).
'blocked_three_ctors.goal315'(_G742641,_G742644,_G742647):-makeShare(_G742256,_G742703),makeShare(_G742247,_G742713),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='('three_ctors.Z',_G742703),'Prelude.=:='(_G742713,_G742703)),_G742703),_G742713),_G742641,_G742644,_G742647).

'three_ctors.goal316'(_G744274,_G744275,_G744276):-freeze(_G744275,'blocked_three_ctors.goal316'(_G744274,_G744275,_G744276)).
'blocked_three_ctors.goal316'(_G744704,_G744707,_G744710):-makeShare(_G744319,_G744772),makeShare(_G744310,_G744782),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G744772,'three_ctors.Z'),'Prelude.=:='(_G744772,_G744782)),_G744782),_G744782),_G744704,_G744707,_G744710).

'three_ctors.goal317'(_G746343,_G746344,_G746345):-freeze(_G746344,'blocked_three_ctors.goal317'(_G746343,_G746344,_G746345)).
'blocked_three_ctors.goal317'(_G746773,_G746776,_G746779):-makeShare(_G746388,_G746835),makeShare(_G746379,_G746845),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G746835,'three_ctors.Z'),'Prelude.=:='(_G746835,_G746845)),_G746835),_G746845),_G746773,_G746776,_G746779).

'three_ctors.goal318'(_G748406,_G748407,_G748408):-freeze(_G748407,'blocked_three_ctors.goal318'(_G748406,_G748407,_G748408)).
'blocked_three_ctors.goal318'(_G748836,_G748839,_G748842):-makeShare(_G748451,_G748904),makeShare(_G748442,_G748914),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='('three_ctors.Z',_G748904),'Prelude.=:='(_G748904,_G748914)),_G748914),_G748914),_G748836,_G748839,_G748842).

'three_ctors.goal319'(_G750475,_G750476,_G750477):-freeze(_G750476,'blocked_three_ctors.goal319'(_G750475,_G750476,_G750477)).
'blocked_three_ctors.goal319'(_G750905,_G750908,_G750911):-makeShare(_G750520,_G750967),makeShare(_G750511,_G750977),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='('three_ctors.Z',_G750967),'Prelude.=:='(_G750967,_G750977)),_G750967),_G750977),_G750905,_G750908,_G750911).

'three_ctors.goal404'(_G752538,_G752539,_G752540):-freeze(_G752539,'blocked_three_ctors.goal404'(_G752538,_G752539,_G752540)).
'blocked_three_ctors.goal404'(_G752968,_G752971,_G752974):-makeShare(_G752574,_G753036),makeShare(_G752583,_G753046),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G753036,_G753046),'Prelude.=:='(_G753046,'three_ctors.Z')),_G753036),_G753046),_G752968,_G752971,_G752974).

'three_ctors.goal405'(_G754607,_G754608,_G754609):-freeze(_G754608,'blocked_three_ctors.goal405'(_G754607,_G754608,_G754609)).
'blocked_three_ctors.goal405'(_G755037,_G755040,_G755043):-makeShare(_G754652,_G755111),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G754643,_G755111),'Prelude.=:='(_G755111,'three_ctors.Z')),_G755111),_G755111),_G755037,_G755040,_G755043).

'three_ctors.goal406'(_G756569,_G756570,_G756571):-freeze(_G756570,'blocked_three_ctors.goal406'(_G756569,_G756570,_G756571)).
'blocked_three_ctors.goal406'(_G756999,_G757002,_G757005):-makeShare(_G756605,_G757067),makeShare(_G756614,_G757077),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G757067,_G757077),'Prelude.=:='('three_ctors.Z',_G757077)),_G757067),_G757077),_G756999,_G757002,_G757005).

'three_ctors.goal407'(_G758638,_G758639,_G758640):-freeze(_G758639,'blocked_three_ctors.goal407'(_G758638,_G758639,_G758640)).
'blocked_three_ctors.goal407'(_G759068,_G759071,_G759074):-makeShare(_G758683,_G759142),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G758674,_G759142),'Prelude.=:='('three_ctors.Z',_G759142)),_G759142),_G759142),_G759068,_G759071,_G759074).

'three_ctors.goal408'(_G760600,_G760601,_G760602):-freeze(_G760601,'blocked_three_ctors.goal408'(_G760600,_G760601,_G760602)).
'blocked_three_ctors.goal408'(_G761030,_G761033,_G761036):-makeShare(_G760645,_G761092),makeShare(_G760636,_G761102),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G761092,_G761102),'Prelude.=:='(_G761092,'three_ctors.Z')),_G761102),_G761092),_G761030,_G761033,_G761036).

'three_ctors.goal409'(_G762663,_G762664,_G762665):-freeze(_G762664,'blocked_three_ctors.goal409'(_G762663,_G762664,_G762665)).
'blocked_three_ctors.goal409'(_G763093,_G763096,_G763099):-makeShare(_G762708,_G763149),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G763149,_G762699),'Prelude.=:='(_G763149,'three_ctors.Z')),_G763149),_G763149),_G763093,_G763096,_G763099).

'three_ctors.goal410'(_G764607,_G764608,_G764609):-freeze(_G764608,'blocked_three_ctors.goal410'(_G764607,_G764608,_G764609)).
'blocked_three_ctors.goal410'(_G765037,_G765040,_G765043):-makeShare(_G764652,_G765099),makeShare(_G764643,_G765109),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G765099,_G765109),'Prelude.=:='('three_ctors.Z',_G765099)),_G765109),_G765099),_G765037,_G765040,_G765043).

'three_ctors.goal411'(_G766670,_G766671,_G766672):-freeze(_G766671,'blocked_three_ctors.goal411'(_G766670,_G766671,_G766672)).
'blocked_three_ctors.goal411'(_G767100,_G767103,_G767106):-makeShare(_G766715,_G767156),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G767156,_G766706),'Prelude.=:='('three_ctors.Z',_G767156)),_G767156),_G767156),_G767100,_G767103,_G767106).

'three_ctors.goal412'(_G768614,_G768615,_G768616):-freeze(_G768615,'blocked_three_ctors.goal412'(_G768614,_G768615,_G768616)).
'blocked_three_ctors.goal412'(_G769044,_G769047,_G769050):-makeShare(_G768659,_G769106),makeShare(_G768650,_G769116),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G769106,'three_ctors.Z'),'Prelude.=:='(_G769116,_G769106)),_G769116),_G769106),_G769044,_G769047,_G769050).

'three_ctors.goal413'(_G770677,_G770678,_G770679):-freeze(_G770678,'blocked_three_ctors.goal413'(_G770677,_G770678,_G770679)).
'blocked_three_ctors.goal413'(_G771107,_G771110,_G771113):-makeShare(_G770722,_G771163),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G771163,'three_ctors.Z'),'Prelude.=:='(_G770713,_G771163)),_G771163),_G771163),_G771107,_G771110,_G771113).

'three_ctors.goal414'(_G772621,_G772622,_G772623):-freeze(_G772622,'blocked_three_ctors.goal414'(_G772621,_G772622,_G772623)).
'blocked_three_ctors.goal414'(_G773051,_G773054,_G773057):-makeShare(_G772666,_G773113),makeShare(_G772657,_G773123),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='('three_ctors.Z',_G773113),'Prelude.=:='(_G773123,_G773113)),_G773123),_G773113),_G773051,_G773054,_G773057).

'three_ctors.goal415'(_G774684,_G774685,_G774686):-freeze(_G774685,'blocked_three_ctors.goal415'(_G774684,_G774685,_G774686)).
'blocked_three_ctors.goal415'(_G775114,_G775117,_G775120):-makeShare(_G774729,_G775170),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='('three_ctors.Z',_G775170),'Prelude.=:='(_G774720,_G775170)),_G775170),_G775170),_G775114,_G775117,_G775120).

'three_ctors.goal416'(_G776628,_G776629,_G776630):-freeze(_G776629,'blocked_three_ctors.goal416'(_G776628,_G776629,_G776630)).
'blocked_three_ctors.goal416'(_G777058,_G777061,_G777064):-makeShare(_G776673,_G777120),makeShare(_G776664,_G777130),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G777120,'three_ctors.Z'),'Prelude.=:='(_G777120,_G777130)),_G777130),_G777120),_G777058,_G777061,_G777064).

'three_ctors.goal417'(_G778691,_G778692,_G778693):-freeze(_G778692,'blocked_three_ctors.goal417'(_G778691,_G778692,_G778693)).
'blocked_three_ctors.goal417'(_G779121,_G779124,_G779127):-makeShare(_G778736,_G779177),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G779177,'three_ctors.Z'),'Prelude.=:='(_G779177,_G778727)),_G779177),_G779177),_G779121,_G779124,_G779127).

'three_ctors.goal418'(_G780635,_G780636,_G780637):-freeze(_G780636,'blocked_three_ctors.goal418'(_G780635,_G780636,_G780637)).
'blocked_three_ctors.goal418'(_G781065,_G781068,_G781071):-makeShare(_G780680,_G781127),makeShare(_G780671,_G781137),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='('three_ctors.Z',_G781127),'Prelude.=:='(_G781127,_G781137)),_G781137),_G781127),_G781065,_G781068,_G781071).

'three_ctors.goal419'(_G782698,_G782699,_G782700):-freeze(_G782699,'blocked_three_ctors.goal419'(_G782698,_G782699,_G782700)).
'blocked_three_ctors.goal419'(_G783128,_G783131,_G783134):-makeShare(_G782743,_G783184),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='('three_ctors.Z',_G783184),'Prelude.=:='(_G783184,_G782734)),_G783184),_G783184),_G783128,_G783131,_G783134).

'three_ctors.goal504'(_G784642,_G784643,_G784644):-freeze(_G784643,'blocked_three_ctors.goal504'(_G784642,_G784643,_G784644)).
'blocked_three_ctors.goal504'(_G785145,_G785148,_G785151):-makeShare(_G784678,_G785219),makeShare(_G784687,_G785229),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G785219,_G785229),'Prelude.=:='(_G785229,'three_ctors.Z')),_G785219),'Prelude.?'(_G785219,_G785229)),_G785145,_G785148,_G785151).

'three_ctors.goal505'(_G786922,_G786923,_G786924):-freeze(_G786923,'blocked_three_ctors.goal505'(_G786922,_G786923,_G786924)).
'blocked_three_ctors.goal505'(_G787425,_G787428,_G787431):-makeShare(_G786958,_G787505),makeShare(_G786967,_G787515),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G787505,_G787515),'Prelude.=:='(_G787515,'three_ctors.Z')),_G787515),'Prelude.?'(_G787505,_G787515)),_G787425,_G787428,_G787431).

'three_ctors.goal506'(_G789208,_G789209,_G789210):-freeze(_G789209,'blocked_three_ctors.goal506'(_G789208,_G789209,_G789210)).
'blocked_three_ctors.goal506'(_G789711,_G789714,_G789717):-makeShare(_G789244,_G789785),makeShare(_G789253,_G789795),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G789785,_G789795),'Prelude.=:='('three_ctors.Z',_G789795)),_G789785),'Prelude.?'(_G789785,_G789795)),_G789711,_G789714,_G789717).

'three_ctors.goal507'(_G791488,_G791489,_G791490):-freeze(_G791489,'blocked_three_ctors.goal507'(_G791488,_G791489,_G791490)).
'blocked_three_ctors.goal507'(_G791991,_G791994,_G791997):-makeShare(_G791524,_G792071),makeShare(_G791533,_G792081),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G792071,_G792081),'Prelude.=:='('three_ctors.Z',_G792081)),_G792081),'Prelude.?'(_G792071,_G792081)),_G791991,_G791994,_G791997).

'three_ctors.goal508'(_G793774,_G793775,_G793776):-freeze(_G793775,'blocked_three_ctors.goal508'(_G793774,_G793775,_G793776)).
'blocked_three_ctors.goal508'(_G794277,_G794280,_G794283):-makeShare(_G793819,_G794351),makeShare(_G793810,_G794361),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G794351,_G794361),'Prelude.=:='(_G794351,'three_ctors.Z')),_G794361),'Prelude.?'(_G794361,_G794351)),_G794277,_G794280,_G794283).

'three_ctors.goal509'(_G796054,_G796055,_G796056):-freeze(_G796055,'blocked_three_ctors.goal509'(_G796054,_G796055,_G796056)).
'blocked_three_ctors.goal509'(_G796557,_G796560,_G796563):-makeShare(_G796099,_G796625),makeShare(_G796090,_G796635),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G796625,_G796635),'Prelude.=:='(_G796625,'three_ctors.Z')),_G796625),'Prelude.?'(_G796635,_G796625)),_G796557,_G796560,_G796563).

'three_ctors.goal510'(_G798328,_G798329,_G798330):-freeze(_G798329,'blocked_three_ctors.goal510'(_G798328,_G798329,_G798330)).
'blocked_three_ctors.goal510'(_G798831,_G798834,_G798837):-makeShare(_G798373,_G798905),makeShare(_G798364,_G798915),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G798905,_G798915),'Prelude.=:='('three_ctors.Z',_G798905)),_G798915),'Prelude.?'(_G798915,_G798905)),_G798831,_G798834,_G798837).

'three_ctors.goal511'(_G800608,_G800609,_G800610):-freeze(_G800609,'blocked_three_ctors.goal511'(_G800608,_G800609,_G800610)).
'blocked_three_ctors.goal511'(_G801111,_G801114,_G801117):-makeShare(_G800653,_G801179),makeShare(_G800644,_G801189),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G801179,_G801189),'Prelude.=:='('three_ctors.Z',_G801179)),_G801179),'Prelude.?'(_G801189,_G801179)),_G801111,_G801114,_G801117).

'three_ctors.goal512'(_G802882,_G802883,_G802884):-freeze(_G802883,'blocked_three_ctors.goal512'(_G802882,_G802883,_G802884)).
'blocked_three_ctors.goal512'(_G803385,_G803388,_G803391):-makeShare(_G802927,_G803459),makeShare(_G802918,_G803469),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G803459,'three_ctors.Z'),'Prelude.=:='(_G803469,_G803459)),_G803469),'Prelude.?'(_G803469,_G803459)),_G803385,_G803388,_G803391).

'three_ctors.goal513'(_G805162,_G805163,_G805164):-freeze(_G805163,'blocked_three_ctors.goal513'(_G805162,_G805163,_G805164)).
'blocked_three_ctors.goal513'(_G805665,_G805668,_G805671):-makeShare(_G805207,_G805733),makeShare(_G805198,_G805743),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G805733,'three_ctors.Z'),'Prelude.=:='(_G805743,_G805733)),_G805733),'Prelude.?'(_G805743,_G805733)),_G805665,_G805668,_G805671).

'three_ctors.goal514'(_G807436,_G807437,_G807438):-freeze(_G807437,'blocked_three_ctors.goal514'(_G807436,_G807437,_G807438)).
'blocked_three_ctors.goal514'(_G807939,_G807942,_G807945):-makeShare(_G807481,_G808013),makeShare(_G807472,_G808023),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='('three_ctors.Z',_G808013),'Prelude.=:='(_G808023,_G808013)),_G808023),'Prelude.?'(_G808023,_G808013)),_G807939,_G807942,_G807945).

'three_ctors.goal515'(_G809716,_G809717,_G809718):-freeze(_G809717,'blocked_three_ctors.goal515'(_G809716,_G809717,_G809718)).
'blocked_three_ctors.goal515'(_G810219,_G810222,_G810225):-makeShare(_G809761,_G810287),makeShare(_G809752,_G810297),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='('three_ctors.Z',_G810287),'Prelude.=:='(_G810297,_G810287)),_G810287),'Prelude.?'(_G810297,_G810287)),_G810219,_G810222,_G810225).

'three_ctors.goal516'(_G811990,_G811991,_G811992):-freeze(_G811991,'blocked_three_ctors.goal516'(_G811990,_G811991,_G811992)).
'blocked_three_ctors.goal516'(_G812493,_G812496,_G812499):-makeShare(_G812035,_G812567),makeShare(_G812026,_G812577),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G812567,'three_ctors.Z'),'Prelude.=:='(_G812567,_G812577)),_G812577),'Prelude.?'(_G812577,_G812567)),_G812493,_G812496,_G812499).

'three_ctors.goal517'(_G814270,_G814271,_G814272):-freeze(_G814271,'blocked_three_ctors.goal517'(_G814270,_G814271,_G814272)).
'blocked_three_ctors.goal517'(_G814773,_G814776,_G814779):-makeShare(_G814315,_G814841),makeShare(_G814306,_G814851),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G814841,'three_ctors.Z'),'Prelude.=:='(_G814841,_G814851)),_G814841),'Prelude.?'(_G814851,_G814841)),_G814773,_G814776,_G814779).

'three_ctors.goal518'(_G816544,_G816545,_G816546):-freeze(_G816545,'blocked_three_ctors.goal518'(_G816544,_G816545,_G816546)).
'blocked_three_ctors.goal518'(_G817047,_G817050,_G817053):-makeShare(_G816589,_G817121),makeShare(_G816580,_G817131),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='('three_ctors.Z',_G817121),'Prelude.=:='(_G817121,_G817131)),_G817131),'Prelude.?'(_G817131,_G817121)),_G817047,_G817050,_G817053).

'three_ctors.goal519'(_G818824,_G818825,_G818826):-freeze(_G818825,'blocked_three_ctors.goal519'(_G818824,_G818825,_G818826)).
'blocked_three_ctors.goal519'(_G819327,_G819330,_G819333):-makeShare(_G818869,_G819395),makeShare(_G818860,_G819405),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='('three_ctors.Z',_G819395),'Prelude.=:='(_G819395,_G819405)),_G819395),'Prelude.?'(_G819405,_G819395)),_G819327,_G819330,_G819333).

'three_ctors.goal604'(_G821098,_G821099,_G821100):-freeze(_G821099,'blocked_three_ctors.goal604'(_G821098,_G821099,_G821100)).
'blocked_three_ctors.goal604'(_G821601,_G821604,_G821607):-makeShare(_G821134,_G821675),makeShare(_G821143,_G821685),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G821675,_G821685),'Prelude.=:='(_G821685,'three_ctors.Z')),_G821675),'Prelude.?'(_G821685,_G821675)),_G821601,_G821604,_G821607).

'three_ctors.goal605'(_G823378,_G823379,_G823380):-freeze(_G823379,'blocked_three_ctors.goal605'(_G823378,_G823379,_G823380)).
'blocked_three_ctors.goal605'(_G823881,_G823884,_G823887):-makeShare(_G823414,_G823961),makeShare(_G823423,_G823971),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G823961,_G823971),'Prelude.=:='(_G823971,'three_ctors.Z')),_G823971),'Prelude.?'(_G823971,_G823961)),_G823881,_G823884,_G823887).

'three_ctors.goal606'(_G825664,_G825665,_G825666):-freeze(_G825665,'blocked_three_ctors.goal606'(_G825664,_G825665,_G825666)).
'blocked_three_ctors.goal606'(_G826167,_G826170,_G826173):-makeShare(_G825700,_G826241),makeShare(_G825709,_G826251),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G826241,_G826251),'Prelude.=:='('three_ctors.Z',_G826251)),_G826241),'Prelude.?'(_G826251,_G826241)),_G826167,_G826170,_G826173).

'three_ctors.goal607'(_G827944,_G827945,_G827946):-freeze(_G827945,'blocked_three_ctors.goal607'(_G827944,_G827945,_G827946)).
'blocked_three_ctors.goal607'(_G828447,_G828450,_G828453):-makeShare(_G827980,_G828527),makeShare(_G827989,_G828537),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G828527,_G828537),'Prelude.=:='('three_ctors.Z',_G828537)),_G828537),'Prelude.?'(_G828537,_G828527)),_G828447,_G828450,_G828453).

'three_ctors.goal608'(_G830230,_G830231,_G830232):-freeze(_G830231,'blocked_three_ctors.goal608'(_G830230,_G830231,_G830232)).
'blocked_three_ctors.goal608'(_G830733,_G830736,_G830739):-makeShare(_G830275,_G830807),makeShare(_G830266,_G830817),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G830807,_G830817),'Prelude.=:='(_G830807,'three_ctors.Z')),_G830817),'Prelude.?'(_G830807,_G830817)),_G830733,_G830736,_G830739).

'three_ctors.goal609'(_G832510,_G832511,_G832512):-freeze(_G832511,'blocked_three_ctors.goal609'(_G832510,_G832511,_G832512)).
'blocked_three_ctors.goal609'(_G833013,_G833016,_G833019):-makeShare(_G832555,_G833081),makeShare(_G832546,_G833091),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G833081,_G833091),'Prelude.=:='(_G833081,'three_ctors.Z')),_G833081),'Prelude.?'(_G833081,_G833091)),_G833013,_G833016,_G833019).

'three_ctors.goal610'(_G834784,_G834785,_G834786):-freeze(_G834785,'blocked_three_ctors.goal610'(_G834784,_G834785,_G834786)).
'blocked_three_ctors.goal610'(_G835287,_G835290,_G835293):-makeShare(_G834829,_G835361),makeShare(_G834820,_G835371),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G835361,_G835371),'Prelude.=:='('three_ctors.Z',_G835361)),_G835371),'Prelude.?'(_G835361,_G835371)),_G835287,_G835290,_G835293).

'three_ctors.goal611'(_G837064,_G837065,_G837066):-freeze(_G837065,'blocked_three_ctors.goal611'(_G837064,_G837065,_G837066)).
'blocked_three_ctors.goal611'(_G837567,_G837570,_G837573):-makeShare(_G837109,_G837635),makeShare(_G837100,_G837645),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G837635,_G837645),'Prelude.=:='('three_ctors.Z',_G837635)),_G837635),'Prelude.?'(_G837635,_G837645)),_G837567,_G837570,_G837573).

'three_ctors.goal612'(_G839338,_G839339,_G839340):-freeze(_G839339,'blocked_three_ctors.goal612'(_G839338,_G839339,_G839340)).
'blocked_three_ctors.goal612'(_G839841,_G839844,_G839847):-makeShare(_G839383,_G839915),makeShare(_G839374,_G839925),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G839915,'three_ctors.Z'),'Prelude.=:='(_G839925,_G839915)),_G839925),'Prelude.?'(_G839915,_G839925)),_G839841,_G839844,_G839847).

'three_ctors.goal613'(_G841618,_G841619,_G841620):-freeze(_G841619,'blocked_three_ctors.goal613'(_G841618,_G841619,_G841620)).
'blocked_three_ctors.goal613'(_G842121,_G842124,_G842127):-makeShare(_G841663,_G842189),makeShare(_G841654,_G842199),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G842189,'three_ctors.Z'),'Prelude.=:='(_G842199,_G842189)),_G842189),'Prelude.?'(_G842189,_G842199)),_G842121,_G842124,_G842127).

'three_ctors.goal614'(_G843892,_G843893,_G843894):-freeze(_G843893,'blocked_three_ctors.goal614'(_G843892,_G843893,_G843894)).
'blocked_three_ctors.goal614'(_G844395,_G844398,_G844401):-makeShare(_G843937,_G844469),makeShare(_G843928,_G844479),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='('three_ctors.Z',_G844469),'Prelude.=:='(_G844479,_G844469)),_G844479),'Prelude.?'(_G844469,_G844479)),_G844395,_G844398,_G844401).

'three_ctors.goal615'(_G846172,_G846173,_G846174):-freeze(_G846173,'blocked_three_ctors.goal615'(_G846172,_G846173,_G846174)).
'blocked_three_ctors.goal615'(_G846675,_G846678,_G846681):-makeShare(_G846217,_G846743),makeShare(_G846208,_G846753),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='('three_ctors.Z',_G846743),'Prelude.=:='(_G846753,_G846743)),_G846743),'Prelude.?'(_G846743,_G846753)),_G846675,_G846678,_G846681).

'three_ctors.goal616'(_G848446,_G848447,_G848448):-freeze(_G848447,'blocked_three_ctors.goal616'(_G848446,_G848447,_G848448)).
'blocked_three_ctors.goal616'(_G848949,_G848952,_G848955):-makeShare(_G848491,_G849023),makeShare(_G848482,_G849033),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G849023,'three_ctors.Z'),'Prelude.=:='(_G849023,_G849033)),_G849033),'Prelude.?'(_G849023,_G849033)),_G848949,_G848952,_G848955).

'three_ctors.goal617'(_G850726,_G850727,_G850728):-freeze(_G850727,'blocked_three_ctors.goal617'(_G850726,_G850727,_G850728)).
'blocked_three_ctors.goal617'(_G851229,_G851232,_G851235):-makeShare(_G850771,_G851297),makeShare(_G850762,_G851307),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G851297,'three_ctors.Z'),'Prelude.=:='(_G851297,_G851307)),_G851297),'Prelude.?'(_G851297,_G851307)),_G851229,_G851232,_G851235).

'three_ctors.goal618'(_G853000,_G853001,_G853002):-freeze(_G853001,'blocked_three_ctors.goal618'(_G853000,_G853001,_G853002)).
'blocked_three_ctors.goal618'(_G853503,_G853506,_G853509):-makeShare(_G853045,_G853577),makeShare(_G853036,_G853587),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='('three_ctors.Z',_G853577),'Prelude.=:='(_G853577,_G853587)),_G853587),'Prelude.?'(_G853577,_G853587)),_G853503,_G853506,_G853509).

'three_ctors.goal619'(_G855280,_G855281,_G855282):-freeze(_G855281,'blocked_three_ctors.goal619'(_G855280,_G855281,_G855282)).
'blocked_three_ctors.goal619'(_G855783,_G855786,_G855789):-makeShare(_G855325,_G855851),makeShare(_G855316,_G855861),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='('three_ctors.Z',_G855851),'Prelude.=:='(_G855851,_G855861)),_G855851),'Prelude.?'(_G855851,_G855861)),_G855783,_G855786,_G855789).

'three_ctors.goal704'(_G857554,_G857555,_G857556):-freeze(_G857555,'blocked_three_ctors.goal704'(_G857554,_G857555,_G857556)).
'blocked_three_ctors.goal704'(_G857984,_G857987,_G857990):-makeShare(_G857590,_G858046),makeShare(_G857599,_G858056),hnf('Prelude.?'(_G858046,'Prelude.&>'('Prelude.&'('Prelude.=:='(_G858046,_G858056),'Prelude.=:='(_G858056,'three_ctors.Z')),_G858046)),_G857984,_G857987,_G857990).

'three_ctors.goal705'(_G859617,_G859618,_G859619):-freeze(_G859618,'blocked_three_ctors.goal705'(_G859617,_G859618,_G859619)).
'blocked_three_ctors.goal705'(_G860047,_G860050,_G860053):-makeShare(_G859653,_G860115),makeShare(_G859662,_G860125),hnf('Prelude.?'(_G860115,'Prelude.&>'('Prelude.&'('Prelude.=:='(_G860115,_G860125),'Prelude.=:='(_G860125,'three_ctors.Z')),_G860125)),_G860047,_G860050,_G860053).

'three_ctors.goal706'(_G861686,_G861687,_G861688):-freeze(_G861687,'blocked_three_ctors.goal706'(_G861686,_G861687,_G861688)).
'blocked_three_ctors.goal706'(_G862116,_G862119,_G862122):-makeShare(_G861722,_G862178),makeShare(_G861731,_G862188),hnf('Prelude.?'(_G862178,'Prelude.&>'('Prelude.&'('Prelude.=:='(_G862178,_G862188),'Prelude.=:='('three_ctors.Z',_G862188)),_G862178)),_G862116,_G862119,_G862122).

'three_ctors.goal707'(_G863749,_G863750,_G863751):-freeze(_G863750,'blocked_three_ctors.goal707'(_G863749,_G863750,_G863751)).
'blocked_three_ctors.goal707'(_G864179,_G864182,_G864185):-makeShare(_G863785,_G864247),makeShare(_G863794,_G864257),hnf('Prelude.?'(_G864247,'Prelude.&>'('Prelude.&'('Prelude.=:='(_G864247,_G864257),'Prelude.=:='('three_ctors.Z',_G864257)),_G864257)),_G864179,_G864182,_G864185).

'three_ctors.goal708'(_G865818,_G865819,_G865820):-freeze(_G865819,'blocked_three_ctors.goal708'(_G865818,_G865819,_G865820)).
'blocked_three_ctors.goal708'(_G866248,_G866251,_G866254):-makeShare(_G865854,_G866310),makeShare(_G865863,_G866320),hnf('Prelude.?'(_G866310,'Prelude.&>'('Prelude.&'('Prelude.=:='(_G866320,_G866310),'Prelude.=:='(_G866320,'three_ctors.Z')),_G866310)),_G866248,_G866251,_G866254).

'three_ctors.goal709'(_G867881,_G867882,_G867883):-freeze(_G867882,'blocked_three_ctors.goal709'(_G867881,_G867882,_G867883)).
'blocked_three_ctors.goal709'(_G868311,_G868314,_G868317):-makeShare(_G867917,_G868379),makeShare(_G867926,_G868389),hnf('Prelude.?'(_G868379,'Prelude.&>'('Prelude.&'('Prelude.=:='(_G868389,_G868379),'Prelude.=:='(_G868389,'three_ctors.Z')),_G868389)),_G868311,_G868314,_G868317).

'three_ctors.goal710'(_G869950,_G869951,_G869952):-freeze(_G869951,'blocked_three_ctors.goal710'(_G869950,_G869951,_G869952)).
'blocked_three_ctors.goal710'(_G870380,_G870383,_G870386):-makeShare(_G869986,_G870442),makeShare(_G869995,_G870452),hnf('Prelude.?'(_G870442,'Prelude.&>'('Prelude.&'('Prelude.=:='(_G870452,_G870442),'Prelude.=:='('three_ctors.Z',_G870452)),_G870442)),_G870380,_G870383,_G870386).

'three_ctors.goal711'(_G872013,_G872014,_G872015):-freeze(_G872014,'blocked_three_ctors.goal711'(_G872013,_G872014,_G872015)).
'blocked_three_ctors.goal711'(_G872443,_G872446,_G872449):-makeShare(_G872049,_G872511),makeShare(_G872058,_G872521),hnf('Prelude.?'(_G872511,'Prelude.&>'('Prelude.&'('Prelude.=:='(_G872521,_G872511),'Prelude.=:='('three_ctors.Z',_G872521)),_G872521)),_G872443,_G872446,_G872449).

'three_ctors.goal712'(_G874082,_G874083,_G874084):-freeze(_G874083,'blocked_three_ctors.goal712'(_G874082,_G874083,_G874084)).
'blocked_three_ctors.goal712'(_G874512,_G874515,_G874518):-makeShare(_G874118,_G874574),makeShare(_G874127,_G874584),hnf('Prelude.?'(_G874574,'Prelude.&>'('Prelude.&'('Prelude.=:='(_G874584,'three_ctors.Z'),'Prelude.=:='(_G874574,_G874584)),_G874574)),_G874512,_G874515,_G874518).

'three_ctors.goal713'(_G876145,_G876146,_G876147):-freeze(_G876146,'blocked_three_ctors.goal713'(_G876145,_G876146,_G876147)).
'blocked_three_ctors.goal713'(_G876575,_G876578,_G876581):-makeShare(_G876181,_G876643),makeShare(_G876190,_G876653),hnf('Prelude.?'(_G876643,'Prelude.&>'('Prelude.&'('Prelude.=:='(_G876653,'three_ctors.Z'),'Prelude.=:='(_G876643,_G876653)),_G876653)),_G876575,_G876578,_G876581).

'three_ctors.goal714'(_G878214,_G878215,_G878216):-freeze(_G878215,'blocked_three_ctors.goal714'(_G878214,_G878215,_G878216)).
'blocked_three_ctors.goal714'(_G878644,_G878647,_G878650):-makeShare(_G878250,_G878706),makeShare(_G878259,_G878716),hnf('Prelude.?'(_G878706,'Prelude.&>'('Prelude.&'('Prelude.=:='('three_ctors.Z',_G878716),'Prelude.=:='(_G878706,_G878716)),_G878706)),_G878644,_G878647,_G878650).

'three_ctors.goal715'(_G880277,_G880278,_G880279):-freeze(_G880278,'blocked_three_ctors.goal715'(_G880277,_G880278,_G880279)).
'blocked_three_ctors.goal715'(_G880707,_G880710,_G880713):-makeShare(_G880313,_G880775),makeShare(_G880322,_G880785),hnf('Prelude.?'(_G880775,'Prelude.&>'('Prelude.&'('Prelude.=:='('three_ctors.Z',_G880785),'Prelude.=:='(_G880775,_G880785)),_G880785)),_G880707,_G880710,_G880713).

'three_ctors.goal716'(_G882346,_G882347,_G882348):-freeze(_G882347,'blocked_three_ctors.goal716'(_G882346,_G882347,_G882348)).
'blocked_three_ctors.goal716'(_G882776,_G882779,_G882782):-makeShare(_G882382,_G882838),makeShare(_G882391,_G882848),hnf('Prelude.?'(_G882838,'Prelude.&>'('Prelude.&'('Prelude.=:='(_G882848,'three_ctors.Z'),'Prelude.=:='(_G882848,_G882838)),_G882838)),_G882776,_G882779,_G882782).

'three_ctors.goal717'(_G884409,_G884410,_G884411):-freeze(_G884410,'blocked_three_ctors.goal717'(_G884409,_G884410,_G884411)).
'blocked_three_ctors.goal717'(_G884839,_G884842,_G884845):-makeShare(_G884445,_G884907),makeShare(_G884454,_G884917),hnf('Prelude.?'(_G884907,'Prelude.&>'('Prelude.&'('Prelude.=:='(_G884917,'three_ctors.Z'),'Prelude.=:='(_G884917,_G884907)),_G884917)),_G884839,_G884842,_G884845).

'three_ctors.goal718'(_G886478,_G886479,_G886480):-freeze(_G886479,'blocked_three_ctors.goal718'(_G886478,_G886479,_G886480)).
'blocked_three_ctors.goal718'(_G886908,_G886911,_G886914):-makeShare(_G886514,_G886970),makeShare(_G886523,_G886980),hnf('Prelude.?'(_G886970,'Prelude.&>'('Prelude.&'('Prelude.=:='('three_ctors.Z',_G886980),'Prelude.=:='(_G886980,_G886970)),_G886970)),_G886908,_G886911,_G886914).

'three_ctors.goal719'(_G888541,_G888542,_G888543):-freeze(_G888542,'blocked_three_ctors.goal719'(_G888541,_G888542,_G888543)).
'blocked_three_ctors.goal719'(_G888971,_G888974,_G888977):-makeShare(_G888577,_G889039),makeShare(_G888586,_G889049),hnf('Prelude.?'(_G889039,'Prelude.&>'('Prelude.&'('Prelude.=:='('three_ctors.Z',_G889049),'Prelude.=:='(_G889049,_G889039)),_G889049)),_G888971,_G888974,_G888977).

'three_ctors.goal804'(_G890610,_G890611,_G890612):-freeze(_G890611,'blocked_three_ctors.goal804'(_G890610,_G890611,_G890612)).
'blocked_three_ctors.goal804'(_G891040,_G891043,_G891046):-makeShare(_G890655,_G891102),makeShare(_G890646,_G891112),hnf('Prelude.?'(_G891102,'Prelude.&>'('Prelude.&'('Prelude.=:='(_G891112,_G891102),'Prelude.=:='(_G891102,'three_ctors.Z')),_G891112)),_G891040,_G891043,_G891046).

'three_ctors.goal805'(_G892673,_G892674,_G892675):-freeze(_G892674,'blocked_three_ctors.goal805'(_G892673,_G892674,_G892675)).
'blocked_three_ctors.goal805'(_G893103,_G893106,_G893109):-makeShare(_G892718,_G893159),hnf('Prelude.?'(_G893159,'Prelude.&>'('Prelude.&'('Prelude.=:='(_G892709,_G893159),'Prelude.=:='(_G893159,'three_ctors.Z')),_G893159)),_G893103,_G893106,_G893109).

'three_ctors.goal806'(_G894617,_G894618,_G894619):-freeze(_G894618,'blocked_three_ctors.goal806'(_G894617,_G894618,_G894619)).
'blocked_three_ctors.goal806'(_G895047,_G895050,_G895053):-makeShare(_G894662,_G895109),makeShare(_G894653,_G895119),hnf('Prelude.?'(_G895109,'Prelude.&>'('Prelude.&'('Prelude.=:='(_G895119,_G895109),'Prelude.=:='('three_ctors.Z',_G895109)),_G895119)),_G895047,_G895050,_G895053).

'three_ctors.goal807'(_G896680,_G896681,_G896682):-freeze(_G896681,'blocked_three_ctors.goal807'(_G896680,_G896681,_G896682)).
'blocked_three_ctors.goal807'(_G897110,_G897113,_G897116):-makeShare(_G896725,_G897166),hnf('Prelude.?'(_G897166,'Prelude.&>'('Prelude.&'('Prelude.=:='(_G896716,_G897166),'Prelude.=:='('three_ctors.Z',_G897166)),_G897166)),_G897110,_G897113,_G897116).

'three_ctors.goal808'(_G898624,_G898625,_G898626):-freeze(_G898625,'blocked_three_ctors.goal808'(_G898624,_G898625,_G898626)).
'blocked_three_ctors.goal808'(_G899054,_G899057,_G899060):-makeShare(_G898669,_G899116),makeShare(_G898660,_G899126),hnf('Prelude.?'(_G899116,'Prelude.&>'('Prelude.&'('Prelude.=:='(_G899116,_G899126),'Prelude.=:='(_G899116,'three_ctors.Z')),_G899126)),_G899054,_G899057,_G899060).

'three_ctors.goal809'(_G900687,_G900688,_G900689):-freeze(_G900688,'blocked_three_ctors.goal809'(_G900687,_G900688,_G900689)).
'blocked_three_ctors.goal809'(_G901117,_G901120,_G901123):-makeShare(_G900732,_G901173),hnf('Prelude.?'(_G901173,'Prelude.&>'('Prelude.&'('Prelude.=:='(_G901173,_G900723),'Prelude.=:='(_G901173,'three_ctors.Z')),_G901173)),_G901117,_G901120,_G901123).

'three_ctors.goal810'(_G902631,_G902632,_G902633):-freeze(_G902632,'blocked_three_ctors.goal810'(_G902631,_G902632,_G902633)).
'blocked_three_ctors.goal810'(_G903061,_G903064,_G903067):-makeShare(_G902676,_G903123),makeShare(_G902667,_G903133),hnf('Prelude.?'(_G903123,'Prelude.&>'('Prelude.&'('Prelude.=:='(_G903123,_G903133),'Prelude.=:='('three_ctors.Z',_G903123)),_G903133)),_G903061,_G903064,_G903067).

'three_ctors.goal811'(_G904694,_G904695,_G904696):-freeze(_G904695,'blocked_three_ctors.goal811'(_G904694,_G904695,_G904696)).
'blocked_three_ctors.goal811'(_G905124,_G905127,_G905130):-makeShare(_G904739,_G905180),hnf('Prelude.?'(_G905180,'Prelude.&>'('Prelude.&'('Prelude.=:='(_G905180,_G904730),'Prelude.=:='('three_ctors.Z',_G905180)),_G905180)),_G905124,_G905127,_G905130).

'three_ctors.goal812'(_G906638,_G906639,_G906640):-freeze(_G906639,'blocked_three_ctors.goal812'(_G906638,_G906639,_G906640)).
'blocked_three_ctors.goal812'(_G907068,_G907071,_G907074):-makeShare(_G906683,_G907130),makeShare(_G906674,_G907140),hnf('Prelude.?'(_G907130,'Prelude.&>'('Prelude.&'('Prelude.=:='(_G907130,'three_ctors.Z'),'Prelude.=:='(_G907140,_G907130)),_G907140)),_G907068,_G907071,_G907074).

'three_ctors.goal813'(_G908701,_G908702,_G908703):-freeze(_G908702,'blocked_three_ctors.goal813'(_G908701,_G908702,_G908703)).
'blocked_three_ctors.goal813'(_G909131,_G909134,_G909137):-makeShare(_G908746,_G909187),hnf('Prelude.?'(_G909187,'Prelude.&>'('Prelude.&'('Prelude.=:='(_G909187,'three_ctors.Z'),'Prelude.=:='(_G908737,_G909187)),_G909187)),_G909131,_G909134,_G909137).

'three_ctors.goal814'(_G910645,_G910646,_G910647):-freeze(_G910646,'blocked_three_ctors.goal814'(_G910645,_G910646,_G910647)).
'blocked_three_ctors.goal814'(_G911075,_G911078,_G911081):-makeShare(_G910690,_G911137),makeShare(_G910681,_G911147),hnf('Prelude.?'(_G911137,'Prelude.&>'('Prelude.&'('Prelude.=:='('three_ctors.Z',_G911137),'Prelude.=:='(_G911147,_G911137)),_G911147)),_G911075,_G911078,_G911081).

'three_ctors.goal815'(_G912708,_G912709,_G912710):-freeze(_G912709,'blocked_three_ctors.goal815'(_G912708,_G912709,_G912710)).
'blocked_three_ctors.goal815'(_G913138,_G913141,_G913144):-makeShare(_G912753,_G913194),hnf('Prelude.?'(_G913194,'Prelude.&>'('Prelude.&'('Prelude.=:='('three_ctors.Z',_G913194),'Prelude.=:='(_G912744,_G913194)),_G913194)),_G913138,_G913141,_G913144).

'three_ctors.goal816'(_G914652,_G914653,_G914654):-freeze(_G914653,'blocked_three_ctors.goal816'(_G914652,_G914653,_G914654)).
'blocked_three_ctors.goal816'(_G915082,_G915085,_G915088):-makeShare(_G914697,_G915144),makeShare(_G914688,_G915154),hnf('Prelude.?'(_G915144,'Prelude.&>'('Prelude.&'('Prelude.=:='(_G915144,'three_ctors.Z'),'Prelude.=:='(_G915144,_G915154)),_G915154)),_G915082,_G915085,_G915088).

'three_ctors.goal817'(_G916715,_G916716,_G916717):-freeze(_G916716,'blocked_three_ctors.goal817'(_G916715,_G916716,_G916717)).
'blocked_three_ctors.goal817'(_G917145,_G917148,_G917151):-makeShare(_G916760,_G917201),hnf('Prelude.?'(_G917201,'Prelude.&>'('Prelude.&'('Prelude.=:='(_G917201,'three_ctors.Z'),'Prelude.=:='(_G917201,_G916751)),_G917201)),_G917145,_G917148,_G917151).

'three_ctors.goal818'(_G918659,_G918660,_G918661):-freeze(_G918660,'blocked_three_ctors.goal818'(_G918659,_G918660,_G918661)).
'blocked_three_ctors.goal818'(_G919089,_G919092,_G919095):-makeShare(_G918704,_G919151),makeShare(_G918695,_G919161),hnf('Prelude.?'(_G919151,'Prelude.&>'('Prelude.&'('Prelude.=:='('three_ctors.Z',_G919151),'Prelude.=:='(_G919151,_G919161)),_G919161)),_G919089,_G919092,_G919095).

'three_ctors.goal819'(_G920722,_G920723,_G920724):-freeze(_G920723,'blocked_three_ctors.goal819'(_G920722,_G920723,_G920724)).
'blocked_three_ctors.goal819'(_G921152,_G921155,_G921158):-makeShare(_G920767,_G921208),hnf('Prelude.?'(_G921208,'Prelude.&>'('Prelude.&'('Prelude.=:='('three_ctors.Z',_G921208),'Prelude.=:='(_G921208,_G920758)),_G921208)),_G921152,_G921155,_G921158).

'three_ctors.goal904'(_G922666,_G922667,_G922668):-freeze(_G922667,'blocked_three_ctors.goal904'(_G922666,_G922667,_G922668)).
'blocked_three_ctors.goal904'(_G923169,_G923172,_G923175):-makeShare(_G922702,_G923243),makeShare(_G922711,_G923253),hnf('Prelude.?'(_G923243,'Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G923243,_G923253),'Prelude.=:='(_G923253,'three_ctors.Z')),_G923243),_G923253)),_G923169,_G923172,_G923175).

'three_ctors.goal905'(_G924946,_G924947,_G924948):-freeze(_G924947,'blocked_three_ctors.goal905'(_G924946,_G924947,_G924948)).
'blocked_three_ctors.goal905'(_G925449,_G925452,_G925455):-makeShare(_G924982,_G925529),makeShare(_G924991,_G925539),hnf('Prelude.?'(_G925529,'Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G925529,_G925539),'Prelude.=:='(_G925539,'three_ctors.Z')),_G925539),_G925539)),_G925449,_G925452,_G925455).

'three_ctors.goal906'(_G927232,_G927233,_G927234):-freeze(_G927233,'blocked_three_ctors.goal906'(_G927232,_G927233,_G927234)).
'blocked_three_ctors.goal906'(_G927735,_G927738,_G927741):-makeShare(_G927268,_G927809),makeShare(_G927277,_G927819),hnf('Prelude.?'(_G927809,'Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G927809,_G927819),'Prelude.=:='('three_ctors.Z',_G927819)),_G927809),_G927819)),_G927735,_G927738,_G927741).

'three_ctors.goal907'(_G929512,_G929513,_G929514):-freeze(_G929513,'blocked_three_ctors.goal907'(_G929512,_G929513,_G929514)).
'blocked_three_ctors.goal907'(_G930015,_G930018,_G930021):-makeShare(_G929548,_G930095),makeShare(_G929557,_G930105),hnf('Prelude.?'(_G930095,'Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G930095,_G930105),'Prelude.=:='('three_ctors.Z',_G930105)),_G930105),_G930105)),_G930015,_G930018,_G930021).

'three_ctors.goal908'(_G931798,_G931799,_G931800):-freeze(_G931799,'blocked_three_ctors.goal908'(_G931798,_G931799,_G931800)).
'blocked_three_ctors.goal908'(_G932301,_G932304,_G932307):-makeShare(_G931834,_G932375),makeShare(_G931843,_G932385),hnf('Prelude.?'(_G932375,'Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G932385,_G932375),'Prelude.=:='(_G932385,'three_ctors.Z')),_G932375),_G932385)),_G932301,_G932304,_G932307).

'three_ctors.goal909'(_G934078,_G934079,_G934080):-freeze(_G934079,'blocked_three_ctors.goal909'(_G934078,_G934079,_G934080)).
'blocked_three_ctors.goal909'(_G934581,_G934584,_G934587):-makeShare(_G934114,_G934661),makeShare(_G934123,_G934671),hnf('Prelude.?'(_G934661,'Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G934671,_G934661),'Prelude.=:='(_G934671,'three_ctors.Z')),_G934671),_G934671)),_G934581,_G934584,_G934587).

'three_ctors.goal910'(_G936364,_G936365,_G936366):-freeze(_G936365,'blocked_three_ctors.goal910'(_G936364,_G936365,_G936366)).
'blocked_three_ctors.goal910'(_G936867,_G936870,_G936873):-makeShare(_G936400,_G936941),makeShare(_G936409,_G936951),hnf('Prelude.?'(_G936941,'Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G936951,_G936941),'Prelude.=:='('three_ctors.Z',_G936951)),_G936941),_G936951)),_G936867,_G936870,_G936873).

'three_ctors.goal911'(_G938644,_G938645,_G938646):-freeze(_G938645,'blocked_three_ctors.goal911'(_G938644,_G938645,_G938646)).
'blocked_three_ctors.goal911'(_G939147,_G939150,_G939153):-makeShare(_G938680,_G939227),makeShare(_G938689,_G939237),hnf('Prelude.?'(_G939227,'Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G939237,_G939227),'Prelude.=:='('three_ctors.Z',_G939237)),_G939237),_G939237)),_G939147,_G939150,_G939153).

'three_ctors.goal912'(_G940930,_G940931,_G940932):-freeze(_G940931,'blocked_three_ctors.goal912'(_G940930,_G940931,_G940932)).
'blocked_three_ctors.goal912'(_G941433,_G941436,_G941439):-makeShare(_G940966,_G941507),makeShare(_G940975,_G941517),hnf('Prelude.?'(_G941507,'Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G941517,'three_ctors.Z'),'Prelude.=:='(_G941507,_G941517)),_G941507),_G941517)),_G941433,_G941436,_G941439).

'three_ctors.goal913'(_G943210,_G943211,_G943212):-freeze(_G943211,'blocked_three_ctors.goal913'(_G943210,_G943211,_G943212)).
'blocked_three_ctors.goal913'(_G943713,_G943716,_G943719):-makeShare(_G943246,_G943793),makeShare(_G943255,_G943803),hnf('Prelude.?'(_G943793,'Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G943803,'three_ctors.Z'),'Prelude.=:='(_G943793,_G943803)),_G943803),_G943803)),_G943713,_G943716,_G943719).

'three_ctors.goal914'(_G945496,_G945497,_G945498):-freeze(_G945497,'blocked_three_ctors.goal914'(_G945496,_G945497,_G945498)).
'blocked_three_ctors.goal914'(_G945999,_G946002,_G946005):-makeShare(_G945532,_G946073),makeShare(_G945541,_G946083),hnf('Prelude.?'(_G946073,'Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='('three_ctors.Z',_G946083),'Prelude.=:='(_G946073,_G946083)),_G946073),_G946083)),_G945999,_G946002,_G946005).

'three_ctors.goal915'(_G947776,_G947777,_G947778):-freeze(_G947777,'blocked_three_ctors.goal915'(_G947776,_G947777,_G947778)).
'blocked_three_ctors.goal915'(_G948279,_G948282,_G948285):-makeShare(_G947812,_G948359),makeShare(_G947821,_G948369),hnf('Prelude.?'(_G948359,'Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='('three_ctors.Z',_G948369),'Prelude.=:='(_G948359,_G948369)),_G948369),_G948369)),_G948279,_G948282,_G948285).

'three_ctors.goal916'(_G950062,_G950063,_G950064):-freeze(_G950063,'blocked_three_ctors.goal916'(_G950062,_G950063,_G950064)).
'blocked_three_ctors.goal916'(_G950565,_G950568,_G950571):-makeShare(_G950098,_G950639),makeShare(_G950107,_G950649),hnf('Prelude.?'(_G950639,'Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G950649,'three_ctors.Z'),'Prelude.=:='(_G950649,_G950639)),_G950639),_G950649)),_G950565,_G950568,_G950571).

'three_ctors.goal917'(_G952342,_G952343,_G952344):-freeze(_G952343,'blocked_three_ctors.goal917'(_G952342,_G952343,_G952344)).
'blocked_three_ctors.goal917'(_G952845,_G952848,_G952851):-makeShare(_G952378,_G952925),makeShare(_G952387,_G952935),hnf('Prelude.?'(_G952925,'Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G952935,'three_ctors.Z'),'Prelude.=:='(_G952935,_G952925)),_G952935),_G952935)),_G952845,_G952848,_G952851).

'three_ctors.goal918'(_G954628,_G954629,_G954630):-freeze(_G954629,'blocked_three_ctors.goal918'(_G954628,_G954629,_G954630)).
'blocked_three_ctors.goal918'(_G955131,_G955134,_G955137):-makeShare(_G954664,_G955205),makeShare(_G954673,_G955215),hnf('Prelude.?'(_G955205,'Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='('three_ctors.Z',_G955215),'Prelude.=:='(_G955215,_G955205)),_G955205),_G955215)),_G955131,_G955134,_G955137).

'three_ctors.goal919'(_G956908,_G956909,_G956910):-freeze(_G956909,'blocked_three_ctors.goal919'(_G956908,_G956909,_G956910)).
'blocked_three_ctors.goal919'(_G957411,_G957414,_G957417):-makeShare(_G956944,_G957491),makeShare(_G956953,_G957501),hnf('Prelude.?'(_G957491,'Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='('three_ctors.Z',_G957501),'Prelude.=:='(_G957501,_G957491)),_G957501),_G957501)),_G957411,_G957414,_G957417).

'three_ctors.goal1004'(_G959212,_G959213,_G959214):-freeze(_G959213,'blocked_three_ctors.goal1004'(_G959212,_G959213,_G959214)).
'blocked_three_ctors.goal1004'(_G959715,_G959718,_G959721):-makeShare(_G959257,_G959789),makeShare(_G959248,_G959799),hnf('Prelude.?'(_G959789,'Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G959799,_G959789),'Prelude.=:='(_G959789,'three_ctors.Z')),_G959799),_G959799)),_G959715,_G959718,_G959721).

'three_ctors.goal1005'(_G961513,_G961514,_G961515):-freeze(_G961514,'blocked_three_ctors.goal1005'(_G961513,_G961514,_G961515)).
'blocked_three_ctors.goal1005'(_G962016,_G962019,_G962022):-makeShare(_G961558,_G962084),makeShare(_G961549,_G962094),hnf('Prelude.?'(_G962084,'Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G962094,_G962084),'Prelude.=:='(_G962084,'three_ctors.Z')),_G962084),_G962094)),_G962016,_G962019,_G962022).

'three_ctors.goal1006'(_G963808,_G963809,_G963810):-freeze(_G963809,'blocked_three_ctors.goal1006'(_G963808,_G963809,_G963810)).
'blocked_three_ctors.goal1006'(_G964311,_G964314,_G964317):-makeShare(_G963853,_G964385),makeShare(_G963844,_G964395),hnf('Prelude.?'(_G964385,'Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G964395,_G964385),'Prelude.=:='('three_ctors.Z',_G964385)),_G964395),_G964395)),_G964311,_G964314,_G964317).

'three_ctors.goal1007'(_G966109,_G966110,_G966111):-freeze(_G966110,'blocked_three_ctors.goal1007'(_G966109,_G966110,_G966111)).
'blocked_three_ctors.goal1007'(_G966612,_G966615,_G966618):-makeShare(_G966154,_G966680),makeShare(_G966145,_G966690),hnf('Prelude.?'(_G966680,'Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G966690,_G966680),'Prelude.=:='('three_ctors.Z',_G966680)),_G966680),_G966690)),_G966612,_G966615,_G966618).

'three_ctors.goal1008'(_G968404,_G968405,_G968406):-freeze(_G968405,'blocked_three_ctors.goal1008'(_G968404,_G968405,_G968406)).
'blocked_three_ctors.goal1008'(_G968907,_G968910,_G968913):-makeShare(_G968449,_G968981),makeShare(_G968440,_G968991),hnf('Prelude.?'(_G968981,'Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G968981,_G968991),'Prelude.=:='(_G968981,'three_ctors.Z')),_G968991),_G968991)),_G968907,_G968910,_G968913).

'three_ctors.goal1009'(_G970705,_G970706,_G970707):-freeze(_G970706,'blocked_three_ctors.goal1009'(_G970705,_G970706,_G970707)).
'blocked_three_ctors.goal1009'(_G971208,_G971211,_G971214):-makeShare(_G970750,_G971276),makeShare(_G970741,_G971286),hnf('Prelude.?'(_G971276,'Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G971276,_G971286),'Prelude.=:='(_G971276,'three_ctors.Z')),_G971276),_G971286)),_G971208,_G971211,_G971214).

'three_ctors.goal1010'(_G973000,_G973001,_G973002):-freeze(_G973001,'blocked_three_ctors.goal1010'(_G973000,_G973001,_G973002)).
'blocked_three_ctors.goal1010'(_G973503,_G973506,_G973509):-makeShare(_G973045,_G973577),makeShare(_G973036,_G973587),hnf('Prelude.?'(_G973577,'Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G973577,_G973587),'Prelude.=:='('three_ctors.Z',_G973577)),_G973587),_G973587)),_G973503,_G973506,_G973509).

'three_ctors.goal1011'(_G975301,_G975302,_G975303):-freeze(_G975302,'blocked_three_ctors.goal1011'(_G975301,_G975302,_G975303)).
'blocked_three_ctors.goal1011'(_G975804,_G975807,_G975810):-makeShare(_G975346,_G975872),makeShare(_G975337,_G975882),hnf('Prelude.?'(_G975872,'Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G975872,_G975882),'Prelude.=:='('three_ctors.Z',_G975872)),_G975872),_G975882)),_G975804,_G975807,_G975810).

'three_ctors.goal1012'(_G977596,_G977597,_G977598):-freeze(_G977597,'blocked_three_ctors.goal1012'(_G977596,_G977597,_G977598)).
'blocked_three_ctors.goal1012'(_G978099,_G978102,_G978105):-makeShare(_G977641,_G978173),makeShare(_G977632,_G978183),hnf('Prelude.?'(_G978173,'Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G978173,'three_ctors.Z'),'Prelude.=:='(_G978183,_G978173)),_G978183),_G978183)),_G978099,_G978102,_G978105).

'three_ctors.goal1013'(_G979897,_G979898,_G979899):-freeze(_G979898,'blocked_three_ctors.goal1013'(_G979897,_G979898,_G979899)).
'blocked_three_ctors.goal1013'(_G980400,_G980403,_G980406):-makeShare(_G979942,_G980468),makeShare(_G979933,_G980478),hnf('Prelude.?'(_G980468,'Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G980468,'three_ctors.Z'),'Prelude.=:='(_G980478,_G980468)),_G980468),_G980478)),_G980400,_G980403,_G980406).

'three_ctors.goal1014'(_G982192,_G982193,_G982194):-freeze(_G982193,'blocked_three_ctors.goal1014'(_G982192,_G982193,_G982194)).
'blocked_three_ctors.goal1014'(_G982695,_G982698,_G982701):-makeShare(_G982237,_G982769),makeShare(_G982228,_G982779),hnf('Prelude.?'(_G982769,'Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='('three_ctors.Z',_G982769),'Prelude.=:='(_G982779,_G982769)),_G982779),_G982779)),_G982695,_G982698,_G982701).

'three_ctors.goal1015'(_G984493,_G984494,_G984495):-freeze(_G984494,'blocked_three_ctors.goal1015'(_G984493,_G984494,_G984495)).
'blocked_three_ctors.goal1015'(_G984996,_G984999,_G985002):-makeShare(_G984538,_G985064),makeShare(_G984529,_G985074),hnf('Prelude.?'(_G985064,'Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='('three_ctors.Z',_G985064),'Prelude.=:='(_G985074,_G985064)),_G985064),_G985074)),_G984996,_G984999,_G985002).

'three_ctors.goal1016'(_G986788,_G986789,_G986790):-freeze(_G986789,'blocked_three_ctors.goal1016'(_G986788,_G986789,_G986790)).
'blocked_three_ctors.goal1016'(_G987291,_G987294,_G987297):-makeShare(_G986833,_G987365),makeShare(_G986824,_G987375),hnf('Prelude.?'(_G987365,'Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G987365,'three_ctors.Z'),'Prelude.=:='(_G987365,_G987375)),_G987375),_G987375)),_G987291,_G987294,_G987297).

'three_ctors.goal1017'(_G989089,_G989090,_G989091):-freeze(_G989090,'blocked_three_ctors.goal1017'(_G989089,_G989090,_G989091)).
'blocked_three_ctors.goal1017'(_G989592,_G989595,_G989598):-makeShare(_G989134,_G989660),makeShare(_G989125,_G989670),hnf('Prelude.?'(_G989660,'Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G989660,'three_ctors.Z'),'Prelude.=:='(_G989660,_G989670)),_G989660),_G989670)),_G989592,_G989595,_G989598).

'three_ctors.goal1018'(_G991384,_G991385,_G991386):-freeze(_G991385,'blocked_three_ctors.goal1018'(_G991384,_G991385,_G991386)).
'blocked_three_ctors.goal1018'(_G991887,_G991890,_G991893):-makeShare(_G991429,_G991961),makeShare(_G991420,_G991971),hnf('Prelude.?'(_G991961,'Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='('three_ctors.Z',_G991961),'Prelude.=:='(_G991961,_G991971)),_G991971),_G991971)),_G991887,_G991890,_G991893).

'three_ctors.goal1019'(_G993685,_G993686,_G993687):-freeze(_G993686,'blocked_three_ctors.goal1019'(_G993685,_G993686,_G993687)).
'blocked_three_ctors.goal1019'(_G994188,_G994191,_G994194):-makeShare(_G993730,_G994256),makeShare(_G993721,_G994266),hnf('Prelude.?'(_G994256,'Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='('three_ctors.Z',_G994256),'Prelude.=:='(_G994256,_G994266)),_G994256),_G994266)),_G994188,_G994191,_G994194).

'three_ctors.goal1104'(_G995980,_G995981,_G995982):-freeze(_G995981,'blocked_three_ctors.goal1104'(_G995980,_G995981,_G995982)).
'blocked_three_ctors.goal1104'(_G996483,_G996486,_G996489):-makeShare(_G996016,_G996557),makeShare(_G996025,_G996567),hnf('Prelude.?'(_G996557,'Prelude.?'(_G996567,'Prelude.&>'('Prelude.&'('Prelude.=:='(_G996557,_G996567),'Prelude.=:='(_G996567,'three_ctors.Z')),_G996557))),_G996483,_G996486,_G996489).

'three_ctors.goal1105'(_G998281,_G998282,_G998283):-freeze(_G998282,'blocked_three_ctors.goal1105'(_G998281,_G998282,_G998283)).
'blocked_three_ctors.goal1105'(_G998784,_G998787,_G998790):-makeShare(_G998317,_G998864),makeShare(_G998326,_G998874),hnf('Prelude.?'(_G998864,'Prelude.?'(_G998874,'Prelude.&>'('Prelude.&'('Prelude.=:='(_G998864,_G998874),'Prelude.=:='(_G998874,'three_ctors.Z')),_G998874))),_G998784,_G998787,_G998790).

'three_ctors.goal1106'(_G1000588,_G1000589,_G1000590):-freeze(_G1000589,'blocked_three_ctors.goal1106'(_G1000588,_G1000589,_G1000590)).
'blocked_three_ctors.goal1106'(_G1001091,_G1001094,_G1001097):-makeShare(_G1000624,_G1001165),makeShare(_G1000633,_G1001175),hnf('Prelude.?'(_G1001165,'Prelude.?'(_G1001175,'Prelude.&>'('Prelude.&'('Prelude.=:='(_G1001165,_G1001175),'Prelude.=:='('three_ctors.Z',_G1001175)),_G1001165))),_G1001091,_G1001094,_G1001097).

'three_ctors.goal1107'(_G1002889,_G1002890,_G1002891):-freeze(_G1002890,'blocked_three_ctors.goal1107'(_G1002889,_G1002890,_G1002891)).
'blocked_three_ctors.goal1107'(_G1003392,_G1003395,_G1003398):-makeShare(_G1002925,_G1003472),makeShare(_G1002934,_G1003482),hnf('Prelude.?'(_G1003472,'Prelude.?'(_G1003482,'Prelude.&>'('Prelude.&'('Prelude.=:='(_G1003472,_G1003482),'Prelude.=:='('three_ctors.Z',_G1003482)),_G1003482))),_G1003392,_G1003395,_G1003398).

'three_ctors.goal1108'(_G1005196,_G1005197,_G1005198):-freeze(_G1005197,'blocked_three_ctors.goal1108'(_G1005196,_G1005197,_G1005198)).
'blocked_three_ctors.goal1108'(_G1005699,_G1005702,_G1005705):-makeShare(_G1005232,_G1005773),makeShare(_G1005241,_G1005783),hnf('Prelude.?'(_G1005773,'Prelude.?'(_G1005783,'Prelude.&>'('Prelude.&'('Prelude.=:='(_G1005783,_G1005773),'Prelude.=:='(_G1005783,'three_ctors.Z')),_G1005773))),_G1005699,_G1005702,_G1005705).

'three_ctors.goal1109'(_G1007497,_G1007498,_G1007499):-freeze(_G1007498,'blocked_three_ctors.goal1109'(_G1007497,_G1007498,_G1007499)).
'blocked_three_ctors.goal1109'(_G1008000,_G1008003,_G1008006):-makeShare(_G1007533,_G1008080),makeShare(_G1007542,_G1008090),hnf('Prelude.?'(_G1008080,'Prelude.?'(_G1008090,'Prelude.&>'('Prelude.&'('Prelude.=:='(_G1008090,_G1008080),'Prelude.=:='(_G1008090,'three_ctors.Z')),_G1008090))),_G1008000,_G1008003,_G1008006).

'three_ctors.goal1110'(_G1009804,_G1009805,_G1009806):-freeze(_G1009805,'blocked_three_ctors.goal1110'(_G1009804,_G1009805,_G1009806)).
'blocked_three_ctors.goal1110'(_G1010307,_G1010310,_G1010313):-makeShare(_G1009840,_G1010381),makeShare(_G1009849,_G1010391),hnf('Prelude.?'(_G1010381,'Prelude.?'(_G1010391,'Prelude.&>'('Prelude.&'('Prelude.=:='(_G1010391,_G1010381),'Prelude.=:='('three_ctors.Z',_G1010391)),_G1010381))),_G1010307,_G1010310,_G1010313).

'three_ctors.goal1111'(_G1012105,_G1012106,_G1012107):-freeze(_G1012106,'blocked_three_ctors.goal1111'(_G1012105,_G1012106,_G1012107)).
'blocked_three_ctors.goal1111'(_G1012608,_G1012611,_G1012614):-makeShare(_G1012141,_G1012688),makeShare(_G1012150,_G1012698),hnf('Prelude.?'(_G1012688,'Prelude.?'(_G1012698,'Prelude.&>'('Prelude.&'('Prelude.=:='(_G1012698,_G1012688),'Prelude.=:='('three_ctors.Z',_G1012698)),_G1012698))),_G1012608,_G1012611,_G1012614).

'three_ctors.goal1112'(_G1014412,_G1014413,_G1014414):-freeze(_G1014413,'blocked_three_ctors.goal1112'(_G1014412,_G1014413,_G1014414)).
'blocked_three_ctors.goal1112'(_G1014915,_G1014918,_G1014921):-makeShare(_G1014448,_G1014989),makeShare(_G1014457,_G1014999),hnf('Prelude.?'(_G1014989,'Prelude.?'(_G1014999,'Prelude.&>'('Prelude.&'('Prelude.=:='(_G1014999,'three_ctors.Z'),'Prelude.=:='(_G1014989,_G1014999)),_G1014989))),_G1014915,_G1014918,_G1014921).

'three_ctors.goal1113'(_G1016713,_G1016714,_G1016715):-freeze(_G1016714,'blocked_three_ctors.goal1113'(_G1016713,_G1016714,_G1016715)).
'blocked_three_ctors.goal1113'(_G1017216,_G1017219,_G1017222):-makeShare(_G1016749,_G1017296),makeShare(_G1016758,_G1017306),hnf('Prelude.?'(_G1017296,'Prelude.?'(_G1017306,'Prelude.&>'('Prelude.&'('Prelude.=:='(_G1017306,'three_ctors.Z'),'Prelude.=:='(_G1017296,_G1017306)),_G1017306))),_G1017216,_G1017219,_G1017222).

'three_ctors.goal1114'(_G1019020,_G1019021,_G1019022):-freeze(_G1019021,'blocked_three_ctors.goal1114'(_G1019020,_G1019021,_G1019022)).
'blocked_three_ctors.goal1114'(_G1019523,_G1019526,_G1019529):-makeShare(_G1019056,_G1019597),makeShare(_G1019065,_G1019607),hnf('Prelude.?'(_G1019597,'Prelude.?'(_G1019607,'Prelude.&>'('Prelude.&'('Prelude.=:='('three_ctors.Z',_G1019607),'Prelude.=:='(_G1019597,_G1019607)),_G1019597))),_G1019523,_G1019526,_G1019529).

'three_ctors.goal1115'(_G1021321,_G1021322,_G1021323):-freeze(_G1021322,'blocked_three_ctors.goal1115'(_G1021321,_G1021322,_G1021323)).
'blocked_three_ctors.goal1115'(_G1021824,_G1021827,_G1021830):-makeShare(_G1021357,_G1021904),makeShare(_G1021366,_G1021914),hnf('Prelude.?'(_G1021904,'Prelude.?'(_G1021914,'Prelude.&>'('Prelude.&'('Prelude.=:='('three_ctors.Z',_G1021914),'Prelude.=:='(_G1021904,_G1021914)),_G1021914))),_G1021824,_G1021827,_G1021830).

'three_ctors.goal1116'(_G1023628,_G1023629,_G1023630):-freeze(_G1023629,'blocked_three_ctors.goal1116'(_G1023628,_G1023629,_G1023630)).
'blocked_three_ctors.goal1116'(_G1024131,_G1024134,_G1024137):-makeShare(_G1023664,_G1024205),makeShare(_G1023673,_G1024215),hnf('Prelude.?'(_G1024205,'Prelude.?'(_G1024215,'Prelude.&>'('Prelude.&'('Prelude.=:='(_G1024215,'three_ctors.Z'),'Prelude.=:='(_G1024215,_G1024205)),_G1024205))),_G1024131,_G1024134,_G1024137).

'three_ctors.goal1117'(_G1025929,_G1025930,_G1025931):-freeze(_G1025930,'blocked_three_ctors.goal1117'(_G1025929,_G1025930,_G1025931)).
'blocked_three_ctors.goal1117'(_G1026432,_G1026435,_G1026438):-makeShare(_G1025965,_G1026512),makeShare(_G1025974,_G1026522),hnf('Prelude.?'(_G1026512,'Prelude.?'(_G1026522,'Prelude.&>'('Prelude.&'('Prelude.=:='(_G1026522,'three_ctors.Z'),'Prelude.=:='(_G1026522,_G1026512)),_G1026522))),_G1026432,_G1026435,_G1026438).

'three_ctors.goal1118'(_G1028236,_G1028237,_G1028238):-freeze(_G1028237,'blocked_three_ctors.goal1118'(_G1028236,_G1028237,_G1028238)).
'blocked_three_ctors.goal1118'(_G1028739,_G1028742,_G1028745):-makeShare(_G1028272,_G1028813),makeShare(_G1028281,_G1028823),hnf('Prelude.?'(_G1028813,'Prelude.?'(_G1028823,'Prelude.&>'('Prelude.&'('Prelude.=:='('three_ctors.Z',_G1028823),'Prelude.=:='(_G1028823,_G1028813)),_G1028813))),_G1028739,_G1028742,_G1028745).

'three_ctors.goal1119'(_G1030537,_G1030538,_G1030539):-freeze(_G1030538,'blocked_three_ctors.goal1119'(_G1030537,_G1030538,_G1030539)).
'blocked_three_ctors.goal1119'(_G1031040,_G1031043,_G1031046):-makeShare(_G1030573,_G1031120),makeShare(_G1030582,_G1031130),hnf('Prelude.?'(_G1031120,'Prelude.?'(_G1031130,'Prelude.&>'('Prelude.&'('Prelude.=:='('three_ctors.Z',_G1031130),'Prelude.=:='(_G1031130,_G1031120)),_G1031130))),_G1031040,_G1031043,_G1031046).

'three_ctors.goal1204'(_G1032844,_G1032845,_G1032846):-freeze(_G1032845,'blocked_three_ctors.goal1204'(_G1032844,_G1032845,_G1032846)).
'blocked_three_ctors.goal1204'(_G1033347,_G1033350,_G1033353):-makeShare(_G1032889,_G1033421),makeShare(_G1032880,_G1033431),hnf('Prelude.?'(_G1033421,'Prelude.?'(_G1033431,'Prelude.&>'('Prelude.&'('Prelude.=:='(_G1033431,_G1033421),'Prelude.=:='(_G1033421,'three_ctors.Z')),_G1033431))),_G1033347,_G1033350,_G1033353).

'three_ctors.goal1205'(_G1035145,_G1035146,_G1035147):-freeze(_G1035146,'blocked_three_ctors.goal1205'(_G1035145,_G1035146,_G1035147)).
'blocked_three_ctors.goal1205'(_G1035648,_G1035651,_G1035654):-makeShare(_G1035190,_G1035716),makeShare(_G1035181,_G1035726),hnf('Prelude.?'(_G1035716,'Prelude.?'(_G1035726,'Prelude.&>'('Prelude.&'('Prelude.=:='(_G1035726,_G1035716),'Prelude.=:='(_G1035716,'three_ctors.Z')),_G1035716))),_G1035648,_G1035651,_G1035654).

'three_ctors.goal1206'(_G1037440,_G1037441,_G1037442):-freeze(_G1037441,'blocked_three_ctors.goal1206'(_G1037440,_G1037441,_G1037442)).
'blocked_three_ctors.goal1206'(_G1037943,_G1037946,_G1037949):-makeShare(_G1037485,_G1038017),makeShare(_G1037476,_G1038027),hnf('Prelude.?'(_G1038017,'Prelude.?'(_G1038027,'Prelude.&>'('Prelude.&'('Prelude.=:='(_G1038027,_G1038017),'Prelude.=:='('three_ctors.Z',_G1038017)),_G1038027))),_G1037943,_G1037946,_G1037949).

'three_ctors.goal1207'(_G1039741,_G1039742,_G1039743):-freeze(_G1039742,'blocked_three_ctors.goal1207'(_G1039741,_G1039742,_G1039743)).
'blocked_three_ctors.goal1207'(_G1040244,_G1040247,_G1040250):-makeShare(_G1039786,_G1040312),makeShare(_G1039777,_G1040322),hnf('Prelude.?'(_G1040312,'Prelude.?'(_G1040322,'Prelude.&>'('Prelude.&'('Prelude.=:='(_G1040322,_G1040312),'Prelude.=:='('three_ctors.Z',_G1040312)),_G1040312))),_G1040244,_G1040247,_G1040250).

'three_ctors.goal1208'(_G1042036,_G1042037,_G1042038):-freeze(_G1042037,'blocked_three_ctors.goal1208'(_G1042036,_G1042037,_G1042038)).
'blocked_three_ctors.goal1208'(_G1042539,_G1042542,_G1042545):-makeShare(_G1042081,_G1042613),makeShare(_G1042072,_G1042623),hnf('Prelude.?'(_G1042613,'Prelude.?'(_G1042623,'Prelude.&>'('Prelude.&'('Prelude.=:='(_G1042613,_G1042623),'Prelude.=:='(_G1042613,'three_ctors.Z')),_G1042623))),_G1042539,_G1042542,_G1042545).

'three_ctors.goal1209'(_G1044337,_G1044338,_G1044339):-freeze(_G1044338,'blocked_three_ctors.goal1209'(_G1044337,_G1044338,_G1044339)).
'blocked_three_ctors.goal1209'(_G1044840,_G1044843,_G1044846):-makeShare(_G1044382,_G1044908),makeShare(_G1044373,_G1044918),hnf('Prelude.?'(_G1044908,'Prelude.?'(_G1044918,'Prelude.&>'('Prelude.&'('Prelude.=:='(_G1044908,_G1044918),'Prelude.=:='(_G1044908,'three_ctors.Z')),_G1044908))),_G1044840,_G1044843,_G1044846).

'three_ctors.goal1210'(_G1046632,_G1046633,_G1046634):-freeze(_G1046633,'blocked_three_ctors.goal1210'(_G1046632,_G1046633,_G1046634)).
'blocked_three_ctors.goal1210'(_G1047135,_G1047138,_G1047141):-makeShare(_G1046677,_G1047209),makeShare(_G1046668,_G1047219),hnf('Prelude.?'(_G1047209,'Prelude.?'(_G1047219,'Prelude.&>'('Prelude.&'('Prelude.=:='(_G1047209,_G1047219),'Prelude.=:='('three_ctors.Z',_G1047209)),_G1047219))),_G1047135,_G1047138,_G1047141).

'three_ctors.goal1211'(_G1048933,_G1048934,_G1048935):-freeze(_G1048934,'blocked_three_ctors.goal1211'(_G1048933,_G1048934,_G1048935)).
'blocked_three_ctors.goal1211'(_G1049436,_G1049439,_G1049442):-makeShare(_G1048978,_G1049504),makeShare(_G1048969,_G1049514),hnf('Prelude.?'(_G1049504,'Prelude.?'(_G1049514,'Prelude.&>'('Prelude.&'('Prelude.=:='(_G1049504,_G1049514),'Prelude.=:='('three_ctors.Z',_G1049504)),_G1049504))),_G1049436,_G1049439,_G1049442).

'three_ctors.goal1212'(_G1051228,_G1051229,_G1051230):-freeze(_G1051229,'blocked_three_ctors.goal1212'(_G1051228,_G1051229,_G1051230)).
'blocked_three_ctors.goal1212'(_G1051731,_G1051734,_G1051737):-makeShare(_G1051273,_G1051805),makeShare(_G1051264,_G1051815),hnf('Prelude.?'(_G1051805,'Prelude.?'(_G1051815,'Prelude.&>'('Prelude.&'('Prelude.=:='(_G1051805,'three_ctors.Z'),'Prelude.=:='(_G1051815,_G1051805)),_G1051815))),_G1051731,_G1051734,_G1051737).

'three_ctors.goal1213'(_G1053529,_G1053530,_G1053531):-freeze(_G1053530,'blocked_three_ctors.goal1213'(_G1053529,_G1053530,_G1053531)).
'blocked_three_ctors.goal1213'(_G1054032,_G1054035,_G1054038):-makeShare(_G1053574,_G1054100),makeShare(_G1053565,_G1054110),hnf('Prelude.?'(_G1054100,'Prelude.?'(_G1054110,'Prelude.&>'('Prelude.&'('Prelude.=:='(_G1054100,'three_ctors.Z'),'Prelude.=:='(_G1054110,_G1054100)),_G1054100))),_G1054032,_G1054035,_G1054038).

'three_ctors.goal1214'(_G1055824,_G1055825,_G1055826):-freeze(_G1055825,'blocked_three_ctors.goal1214'(_G1055824,_G1055825,_G1055826)).
'blocked_three_ctors.goal1214'(_G1056327,_G1056330,_G1056333):-makeShare(_G1055869,_G1056401),makeShare(_G1055860,_G1056411),hnf('Prelude.?'(_G1056401,'Prelude.?'(_G1056411,'Prelude.&>'('Prelude.&'('Prelude.=:='('three_ctors.Z',_G1056401),'Prelude.=:='(_G1056411,_G1056401)),_G1056411))),_G1056327,_G1056330,_G1056333).

'three_ctors.goal1215'(_G1058125,_G1058126,_G1058127):-freeze(_G1058126,'blocked_three_ctors.goal1215'(_G1058125,_G1058126,_G1058127)).
'blocked_three_ctors.goal1215'(_G1058628,_G1058631,_G1058634):-makeShare(_G1058170,_G1058696),makeShare(_G1058161,_G1058706),hnf('Prelude.?'(_G1058696,'Prelude.?'(_G1058706,'Prelude.&>'('Prelude.&'('Prelude.=:='('three_ctors.Z',_G1058696),'Prelude.=:='(_G1058706,_G1058696)),_G1058696))),_G1058628,_G1058631,_G1058634).

'three_ctors.goal1216'(_G1060420,_G1060421,_G1060422):-freeze(_G1060421,'blocked_three_ctors.goal1216'(_G1060420,_G1060421,_G1060422)).
'blocked_three_ctors.goal1216'(_G1060923,_G1060926,_G1060929):-makeShare(_G1060465,_G1060997),makeShare(_G1060456,_G1061007),hnf('Prelude.?'(_G1060997,'Prelude.?'(_G1061007,'Prelude.&>'('Prelude.&'('Prelude.=:='(_G1060997,'three_ctors.Z'),'Prelude.=:='(_G1060997,_G1061007)),_G1061007))),_G1060923,_G1060926,_G1060929).

'three_ctors.goal1217'(_G1062721,_G1062722,_G1062723):-freeze(_G1062722,'blocked_three_ctors.goal1217'(_G1062721,_G1062722,_G1062723)).
'blocked_three_ctors.goal1217'(_G1063224,_G1063227,_G1063230):-makeShare(_G1062766,_G1063292),makeShare(_G1062757,_G1063302),hnf('Prelude.?'(_G1063292,'Prelude.?'(_G1063302,'Prelude.&>'('Prelude.&'('Prelude.=:='(_G1063292,'three_ctors.Z'),'Prelude.=:='(_G1063292,_G1063302)),_G1063292))),_G1063224,_G1063227,_G1063230).

'three_ctors.goal1218'(_G1065016,_G1065017,_G1065018):-freeze(_G1065017,'blocked_three_ctors.goal1218'(_G1065016,_G1065017,_G1065018)).
'blocked_three_ctors.goal1218'(_G1065519,_G1065522,_G1065525):-makeShare(_G1065061,_G1065593),makeShare(_G1065052,_G1065603),hnf('Prelude.?'(_G1065593,'Prelude.?'(_G1065603,'Prelude.&>'('Prelude.&'('Prelude.=:='('three_ctors.Z',_G1065593),'Prelude.=:='(_G1065593,_G1065603)),_G1065603))),_G1065519,_G1065522,_G1065525).

'three_ctors.goal1219'(_G1067317,_G1067318,_G1067319):-freeze(_G1067318,'blocked_three_ctors.goal1219'(_G1067317,_G1067318,_G1067319)).
'blocked_three_ctors.goal1219'(_G1067820,_G1067823,_G1067826):-makeShare(_G1067362,_G1067888),makeShare(_G1067353,_G1067898),hnf('Prelude.?'(_G1067888,'Prelude.?'(_G1067898,'Prelude.&>'('Prelude.&'('Prelude.=:='('three_ctors.Z',_G1067888),'Prelude.=:='(_G1067888,_G1067898)),_G1067888))),_G1067820,_G1067823,_G1067826).

'three_ctors.goal1'(_G1069558,_G1069559,_G1069560):-freeze(_G1069559,'blocked_three_ctors.goal1'(_G1069558,_G1069559,_G1069560)).
'blocked_three_ctors.goal1'(_G1069757,_G1069760,_G1069763):-makeShare(_G1069594,_G1069789),hnf('Prelude.&>'('Prelude.=:='(_G1069789,'three_ctors.A'),_G1069789),_G1069757,_G1069760,_G1069763).

'three_ctors.goal2'(_G1070750,_G1070751,_G1070752):-freeze(_G1070751,'blocked_three_ctors.goal2'(_G1070750,_G1070751,_G1070752)).
'blocked_three_ctors.goal2'(_G1070949,_G1070952,_G1070955):-makeShare(_G1070786,_G1070981),hnf('Prelude.&>'('Prelude.=:='(_G1070981,'three_ctors.B'),_G1070981),_G1070949,_G1070952,_G1070955).

'three_ctors.goal3'(_G1071942,_G1071943,_G1071944):-freeze(_G1071943,'blocked_three_ctors.goal3'(_G1071942,_G1071943,_G1071944)).
'blocked_three_ctors.goal3'(_G1072141,_G1072144,_G1072147):-makeShare(_G1071978,_G1072173),hnf('Prelude.&>'('Prelude.=:='(_G1072173,'three_ctors.C'),_G1072173),_G1072141,_G1072144,_G1072147).

'three_ctors.goal4'(_G1073134,_G1073135,_G1073136):-freeze(_G1073135,'blocked_three_ctors.goal4'(_G1073134,_G1073135,_G1073136)).
'blocked_three_ctors.goal4'(_G1073333,_G1073336,_G1073339):-makeShare(_G1073170,_G1073365),hnf('Prelude.&>'('Prelude.=:='('three_ctors.A',_G1073365),_G1073365),_G1073333,_G1073336,_G1073339).

'three_ctors.goal5'(_G1074326,_G1074327,_G1074328):-freeze(_G1074327,'blocked_three_ctors.goal5'(_G1074326,_G1074327,_G1074328)).
'blocked_three_ctors.goal5'(_G1074525,_G1074528,_G1074531):-makeShare(_G1074362,_G1074557),hnf('Prelude.&>'('Prelude.=:='('three_ctors.B',_G1074557),_G1074557),_G1074525,_G1074528,_G1074531).

'three_ctors.goal6'(_G1075518,_G1075519,_G1075520):-freeze(_G1075519,'blocked_three_ctors.goal6'(_G1075518,_G1075519,_G1075520)).
'blocked_three_ctors.goal6'(_G1075717,_G1075720,_G1075723):-makeShare(_G1075554,_G1075749),hnf('Prelude.&>'('Prelude.=:='('three_ctors.C',_G1075749),_G1075749),_G1075717,_G1075720,_G1075723).

'three_ctors.goal7'(_G1076710,_G1076711,_G1076712):-freeze(_G1076711,'blocked_three_ctors.goal7'(_G1076710,_G1076711,_G1076712)).
'blocked_three_ctors.goal7'(_G1076982,_G1076985,_G1076988):-makeShare(_G1076746,_G1077020),hnf('Prelude.?'('Prelude.&>'('Prelude.=:='(_G1077020,'three_ctors.A'),_G1077020),_G1077020),_G1076982,_G1076985,_G1076988).

'three_ctors.goal8'(_G1078113,_G1078114,_G1078115):-freeze(_G1078114,'blocked_three_ctors.goal8'(_G1078113,_G1078114,_G1078115)).
'blocked_three_ctors.goal8'(_G1078385,_G1078388,_G1078391):-makeShare(_G1078149,_G1078423),hnf('Prelude.?'('Prelude.&>'('Prelude.=:='(_G1078423,'three_ctors.B'),_G1078423),_G1078423),_G1078385,_G1078388,_G1078391).

'three_ctors.goal9'(_G1079516,_G1079517,_G1079518):-freeze(_G1079517,'blocked_three_ctors.goal9'(_G1079516,_G1079517,_G1079518)).
'blocked_three_ctors.goal9'(_G1079788,_G1079791,_G1079794):-makeShare(_G1079552,_G1079826),hnf('Prelude.?'('Prelude.&>'('Prelude.=:='(_G1079826,'three_ctors.C'),_G1079826),_G1079826),_G1079788,_G1079791,_G1079794).

'three_ctors.goal10'(_G1080937,_G1080938,_G1080939):-freeze(_G1080938,'blocked_three_ctors.goal10'(_G1080937,_G1080938,_G1080939)).
'blocked_three_ctors.goal10'(_G1081209,_G1081212,_G1081215):-makeShare(_G1080973,_G1081247),hnf('Prelude.?'('Prelude.&>'('Prelude.=:='('three_ctors.A',_G1081247),_G1081247),_G1081247),_G1081209,_G1081212,_G1081215).

'three_ctors.goal11'(_G1082361,_G1082362,_G1082363):-freeze(_G1082362,'blocked_three_ctors.goal11'(_G1082361,_G1082362,_G1082363)).
'blocked_three_ctors.goal11'(_G1082633,_G1082636,_G1082639):-makeShare(_G1082397,_G1082671),hnf('Prelude.?'('Prelude.&>'('Prelude.=:='('three_ctors.B',_G1082671),_G1082671),_G1082671),_G1082633,_G1082636,_G1082639).

'three_ctors.goal12'(_G1083785,_G1083786,_G1083787):-freeze(_G1083786,'blocked_three_ctors.goal12'(_G1083785,_G1083786,_G1083787)).
'blocked_three_ctors.goal12'(_G1084057,_G1084060,_G1084063):-makeShare(_G1083821,_G1084095),hnf('Prelude.?'('Prelude.&>'('Prelude.=:='('three_ctors.C',_G1084095),_G1084095),_G1084095),_G1084057,_G1084060,_G1084063).

'three_ctors.goal101'(_G1085227,_G1085228,_G1085229):-freeze(_G1085228,'blocked_three_ctors.goal101'(_G1085227,_G1085228,_G1085229)).
'blocked_three_ctors.goal101'(_G1085657,_G1085660,_G1085663):-makeShare(_G1085263,_G1085719),makeShare(_G1085272,_G1085729),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G1085719,_G1085729),'Prelude.=:='(_G1085729,'three_ctors.A')),_G1085719),_G1085719),_G1085657,_G1085660,_G1085663).

'three_ctors.goal102'(_G1087290,_G1087291,_G1087292):-freeze(_G1087291,'blocked_three_ctors.goal102'(_G1087290,_G1087291,_G1087292)).
'blocked_three_ctors.goal102'(_G1087720,_G1087723,_G1087726):-makeShare(_G1087326,_G1087782),makeShare(_G1087335,_G1087792),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G1087782,_G1087792),'Prelude.=:='(_G1087792,'three_ctors.B')),_G1087782),_G1087782),_G1087720,_G1087723,_G1087726).

'three_ctors.goal103'(_G1089353,_G1089354,_G1089355):-freeze(_G1089354,'blocked_three_ctors.goal103'(_G1089353,_G1089354,_G1089355)).
'blocked_three_ctors.goal103'(_G1089783,_G1089786,_G1089789):-makeShare(_G1089389,_G1089845),makeShare(_G1089398,_G1089855),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G1089845,_G1089855),'Prelude.=:='(_G1089855,'three_ctors.C')),_G1089845),_G1089845),_G1089783,_G1089786,_G1089789).

:-costCenters(['']).




%%%%% Number of shared variables: 350
