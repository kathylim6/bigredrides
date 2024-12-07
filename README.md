#bigredrides

Big Red Rides
Share your ride, split the cost: a long-distance car-share app for Cornellians

Link to the IOS Github Repo: https://github.com/rohan-shankar/hack-challenge-real.git


Stuck on an overpriced, broken OurBus? Looking for cheap way to get home for breaks? Big Red Rides is the app for you! 

Big Red Rides lets you easily share long-distance rides before and after breaks with your fellow Cornellians! BRR lets you post your trips to any city, and fellow students can join as riders to help split gas costs. Simply register as a user, post your drive, and enjoy the ride with others while saving money on gas. It’s the perfect way to make your travels more affordable, social, and eco-friendly!

For Drivers: Post your trip to any city, set your estimated total gas costs, and invite riders to join you.
For Riders: Find available trips, book a seat, and split the cost with the driver.

Save money, meet new people, and make your journey to and from Cornell easier. Join Big Red Rides today!


How our app meets the requirements:
- We have GET routes to get all trips and get a specific user
- We have POST routes to add a rider to a trip and to add a rating to a user
- We have a DELETE route to delete a trip
- We have 3 tables in our database file (Users, Trips, Ratings) - User and Trips have a many-to-many relationship (defined by an association table) and Users and Ratings have a one-to-many relationship
- We are also submitting an API specification that explains each implemented route

Other notes for the graders:
- Our IOS team did not have enough time to implement the ratings feature, but we still wanted to include this since we had already implemented this table within our code. 
- We increased the security of our app through authentication, using session tokens and username/password authentication (following previous lectures and demos on Authentication)
