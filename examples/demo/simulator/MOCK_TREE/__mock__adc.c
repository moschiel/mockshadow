//__MOCK_COPY_FILE_CONTENT__
//__MOCK_REPLACE_CODE_START: function ReadBattery
int ReadBattery(void) { return SIM_BATTERY_MV; }
//__MOCK_REPLACE_CODE_END
//__MOCK_TOP_START
#include "__additional__battery.h"
//__MOCK_TOP_END
