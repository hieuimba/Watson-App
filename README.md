# Watson 3
https://share.streamlit.io/hieuimba/watson-app
### Ver 3.2.1 - Oct 24, 2021
##### App Architecture Update
 - Pushed TWS client to server for stable uptime and access availability
 - Scheduled server start and stop time
 - Journal records now automatically imported daily with initial stop & target values
 - Server notifications delivered via Discord webhooks

##### Earnings information
 - Upcoming earnings information added to PSC & watchlist screen

##### Bug fixes:
 - Fixed fractional size issue where quantity returns rounded value*
 - Fixed connection pooling error when database connection timesout after a period of time

<sub><sup>*Work around by importing correct values to journal via watchlist</sup></sub>

---

### Ver 3.1 - Oct 11, 2021
##### New: Watchlist Screen
 - View daily stock setups with potential entries, stops and exits
 - Ability to Add and Delete Watchlist records using text commands
 - Interactive TradingView chart
 
##### "Add to Watchlist" button from PSC screen
 - Ability to add a watch item directly from PSC screen
 
##### Other:
 - Added icon & theme color
 - Post-release fixes

---

### Ver 3.0 - Sep 6, 2021
##### Launch to share.streamlit
