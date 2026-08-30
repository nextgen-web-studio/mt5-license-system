//+------------------------------------------------------------------+
//|                                           InfinityTrader.mq5     |
//|                                              NextGen Web Studio  |
//+------------------------------------------------------------------+
#property copyright "NextGen Web Studio"
#property link      "https://t.me/shridharsan1"
#property version   "1.00"
#property strict

// These two lines are auto-replaced by the compiler with customer values
int ALLOWED_MT5_ID = 123456789;
datetime LICENSE_EXPIRY = D'2099.01.01';

int OnInit()
{
   long current_account = AccountInfoInteger(ACCOUNT_LOGIN);

   if(current_account != ALLOWED_MT5_ID) {
      Print("Invalid MT5 ID. This EA is locked to ID: ", ALLOWED_MT5_ID);
      return INIT_FAILED;
   }

   if(TimeCurrent() > LICENSE_EXPIRY) {
      Print("License expired on: ", LICENSE_EXPIRY);
      return INIT_FAILED;
   }

   Print("Infinity Trader EA initialized. License valid until: ", LICENSE_EXPIRY);
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason) {}

void OnTick()
{
   // Trading logic goes here
}