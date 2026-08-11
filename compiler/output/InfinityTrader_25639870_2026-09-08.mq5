#property strict
#property version "1.00"

input string MT5_ID = "25639870";
input string EXPIRY = "2026-09-08";
input string PLAN   = "EA Basic Plan";

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