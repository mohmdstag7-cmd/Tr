//+------------------------------------------------------------------+
//|                                          CalendarExporter.mq5    |
//|  Exports CalendarValueHistory to CSV for MT5 Trading Workstation |
//|  Phase 5 — Market Data & Analysis                                |
//|  Compilable in MetaEditor (MQL5)                                 |
//+------------------------------------------------------------------+
#property copyright "MT5 Trading Workstation"
#property version   "1.00"
#property script_show_inputs

input string InpFileName = "calendar_export.csv";
input int    InpDaysBack = 30;
input int    InpDaysForward = 7;

//+------------------------------------------------------------------+
//| Script program start function                                    |
//+------------------------------------------------------------------+
void OnStart()
  {
   datetime from = TimeGMT() - InpDaysBack * 86400;
   datetime to   = TimeGMT() + InpDaysForward * 86400;

   MqlCalendarValue values[];
   if(!CalendarValueHistory(values, from, to, NULL, NULL))
     {
      Print("CalendarValueHistory failed, error ", GetLastError());
      return;
     }

   int file = FileOpen(InpFileName, FILE_WRITE | FILE_CSV | FILE_ANSI, ",");
   if(file == INVALID_HANDLE)
     {
      Print("FileOpen failed for ", InpFileName, " error ", GetLastError());
      return;
     }

   // Header
   FileWrite(file, "time", "currency", "impact", "event", "forecast", "previous", "actual");

   for(int i=0; i<ArraySize(values); i++)
     {
      MqlCalendarEvent event;
      MqlCalendarCountry country;
      if(!CalendarEventById(values[i].event_id, event))
         continue;
      if(!CalendarCountryById(event.country_id, country))
         continue;

      string currency = country.currency;
      string impact_str = ImpactToString(event.importance);
      string event_name = event.name;
      // Clean commas to keep CSV valid
      StringReplace(event_name, ",", " ");

      string forecast = "";
      string previous = "";
      string actual = "";

      // Values: actual, forecast, previous are in MqlCalendarValue
      // Use CalendarValueById if needed, but values[i] already has them
      // actual_value, prev_value, forecast_value are long/double depending on type
      // We export as string
      if(values[i].actual_value != 0 || values[i].prev_value != 0 || values[i].forecast_value != 0)
        {
         // Try to get string representation via CalendarValueById
         // Fallback to numeric
         forecast = DoubleToString(values[i].forecast_value, 2);
         previous = DoubleToString(values[i].prev_value, 2);
         actual   = DoubleToString(values[i].actual_value, 2);
        }

      datetime ev_time = values[i].time;
      string time_str = TimeToString(ev_time, TIME_DATE | TIME_MINUTES | TIME_SECONDS);

      FileWrite(file, time_str, currency, impact_str, event_name, forecast, previous, actual);
     }

   FileClose(file);
   Print("Calendar export completed: ", InpFileName, " records=", ArraySize(values));
  }

//+------------------------------------------------------------------+
//| Convert importance enum to string                                |
//+------------------------------------------------------------------+
string ImpactToString(ENUM_CALENDAR_EVENT_IMPORTANCE importance)
  {
   switch(importance)
     {
      case CALENDAR_IMPORTANCE_HIGH:   return "high";
      case CALENDAR_IMPORTANCE_MEDIUM: return "medium";
      case CALENDAR_IMPORTANCE_LOW:    return "low";
      default:                         return "low";
     }
  }
//+------------------------------------------------------------------+
