#property strict
#property version "1.00"

input string MT5_ID = "1123365";
input string EXPIRY = "2026-11-10";
input string PLAN   = "EA gold (3 months)";

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