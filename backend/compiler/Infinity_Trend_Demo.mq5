//+------------------------------------------------------------------+
//|                                     Infinity_Trend_Demo.mq5      |
//|                                  Copyright 2026, Infinity Trader |
//|                                             https://example.com  |
//+------------------------------------------------------------------+
#property copyright "Copyright 2026, Infinity Trader"
#property link      "https://example.com"
#property version   "1.00"

//--- Licensing Variables (Will be replaced by Compiler Worker)
long AllowedMT5Login = 0;
string ExpiryDate = "2026.12.31 23:59:59";

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
  {
   //--- Licensing Checks
   long currentLogin = AccountInfoInteger(ACCOUNT_LOGIN);
   
   if(currentLogin != AllowedMT5Login)
     {
      Alert("License Verification Failed: This EA is not licensed for MT5 Account ", currentLogin);
      Print("License Verification Failed: Expected ", AllowedMT5Login, " but got ", currentLogin);
      ExpertRemove();
      return(INIT_FAILED);
     }
     
   datetime expiry = StringToTime(ExpiryDate);
   if(TimeCurrent() > expiry)
     {
      Alert("License Expired: This EA subscription expired on ", ExpiryDate);
      Print("License Expired on ", ExpiryDate);
      ExpertRemove();
      return(INIT_FAILED);
     }
     
   Print("License Verification Successful for Account ", currentLogin);
   
   //--- Initialization logic here
   
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   //---
  }
//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
  {
   //---
  }
//+------------------------------------------------------------------+
