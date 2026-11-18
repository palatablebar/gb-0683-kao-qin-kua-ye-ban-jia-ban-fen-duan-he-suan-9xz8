TITLE='考勤跨夜班与加班分段核算'
SHORT='shiftledger'
RULE_VERSION='2026.11.18-v2'
MODULES=[('m1_ingest', '打卡采信'), ('m2_mapping', '班次日历'), ('m3_versions', '跨夜配对'),
    ('m3b_handovers', '支援交接'), ('m4_segments', '缺卡复核'), ('m5_calculate', '工时切段'),
    ('m6_reconcile', '薪资对账'), ('m7_archive', '周期归档')]
REQUIRED=['id', 'employee', 'shift_day', 'version', 'punch', 'at', 'shift_start', 'shift_end', 'break_start', 'break_end', 'hourly_rate', 'paid']
NUMERIC=['version', 'hourly_rate', 'paid']
DATES=['shift_day']
TIMES=['at']
# 跨夜支援：交接源（可选第二数据源）的列约定与默认班组
HANDOVER_SAMPLE='handovers_dirty.csv'
HANDOVER_SAMPLES=('handovers_dirty.csv','handovers.csv')
HANDOVER_REQUIRED=['h_id', 'employee', 'shift_day', 'version', 'at', 'to_team']
HANDOVER_NUMERIC=['version']
DEFAULT_TEAM='HOME'
