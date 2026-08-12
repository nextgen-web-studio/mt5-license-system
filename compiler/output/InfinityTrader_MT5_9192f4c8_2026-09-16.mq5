#property strict
#property version "1.00"

input string MT5_ID = "MT5_9192f4c8";
input string EXPIRY = "2026-09-16";
input string PLAN   = "EA Basic Plan (1month)";

int OnInit()
{
   Print("Infinity Trader EA initialized");
   Print("MT5 ID: ", MT5_ID);
   Print("Expiry: ", EXPIRY);
   Print("Plan: ", PLAN);

   return(INIT_SUCCEEDED);
}

void OnTick()
{
}