# Watson 3
https://share.streamlit.io/hieuimba/watson-app
### Ver 3.2.1 - Oct 24, 2021
##### App Architecture Update
 - Pushed TWS client to server for stable uptime and ease of access
 - Scheduled server start and stop time
 - Journal imports now handled automatically with initial stop & target values
 - Server notifications delivered via Discord webhooks

##### Earnings information
 - Upcoming earnings information available in the PSC & watchlist screen

##### Bug fixes:
 - Fix fractional size issue where quantity returns rounded value*
 - Fix connection pooling error when database connection timesout after a period of time

<sub><sup>*Work around by importing correct values to journal via watchlist</sup></sub>

---

### Ver 3.1 - Oct 11, 2021
##### New: Watchlist Screen
 - View daily stock setups with potential entries, stops and exits
 - Ability to Add and Delete Watchlist records using text commands
 - Interactive TradingView chart
 
##### "Add to Watchlist" button from PSC screen
 - Optimize work-flow by sending a watch item directly from PSC screen
 
##### Other:
 - Add icon & theme color
 - Post-release fixes

---

### Ver 3.0 - Sep 6, 2021
##### Launch to share.streamlit
