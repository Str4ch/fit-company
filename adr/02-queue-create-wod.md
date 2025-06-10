## Choices made: 

### STEP 4:
 - Added rabbitmq class, that listens to the createWodQueue and creates WODs
 - Modyfied docker-compose.yml so coach service could use rabbit mq
 - Added multithreading, so service could both send messages through API and listen to queues
 - WodForUser table, here generated wods are saved and retrieved, when needed

### STEP 5:
 - Added 20% failure to wod generating 
 - Now rabbitmq tries 3 times to generate a wod for a user, if did not succed then send to createWodQueue-dead

 ### STEP 6:
 - Cron job, script that sends a request to API endpoint to create the wods

 ## Improvements TODO:

  - Add back-ups(Redis)
  - Add logs and script that cleans them after some time
  - Add a service that cleans old records in WodForUser table