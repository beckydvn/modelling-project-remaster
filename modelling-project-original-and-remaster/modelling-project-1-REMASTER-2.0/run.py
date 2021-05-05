import geopy
import geopy.distance
from geopy.geocoders import Nominatim
import pyproj
import bauhaus
from bauhaus import Encoding, proposition, constraint
import nnf

#SET UP BASIC PROPOSITIONS

global e
e = Encoding()

#class for universal propositions
@proposition(e)
class universal_prop:
  #instantiate with name to be given to the proposition
  def __init__(self, name):
    self.name = name

#class for weather propositions
@proposition(e)
class weather_prop:
  #instantiate with name to be given to the proposition
  def __init__(self, name):
    self.name = name

#class for travel propositions
@proposition(e)
class transit_prop:
  #instantiate with name to be given to the proposition
  def __init__(self, name):
    self.name = name

#class for delay propositions
@proposition(e)
class delay_prop:
  #instantiate with name to be given to the proposition
  def __init__(self, name):
    self.name = name

#factors that might affect the trips
virus = universal_prop('virus') # 🦠 
documents = universal_prop('documents') # document
international = universal_prop('international') # crossing the border
toll_money = universal_prop('money for tolls') # toll money
afford_plane = universal_prop('can afford plane ticket(s)') # plane ticket is affordable
holiday = universal_prop('holiday') # holiday 
more_than_five = universal_prop('more than five people') # travelling with more than 5 people
urgent_trip = universal_prop('trip is urgent') # trip is urgent

#for each factor variables, we're storing them in dictionaries because when asking the users for their inputs,
#there might be multiple stops along the trip, therefore we would need propositions for each stop along the way.
sunny = {}
rainy = {}
snowstorm = {}
roadwork = {}
accident = {}
toll = {}
drive = {}
transit = {} 
plane = {}

#stop_info is a (global) list of dictionaries, where each entry contains the starting    
#and ending location for each stop in user's chosen stops, and the distance between the two.
#(in short it contains all the relevant info for the stops the user will take).
stop_info = []

def read_files(country, filename):
  """read in a database of cities from a specific country and write it to a list 
  of dictionaries"""
  file1 = open(filename, "r")
  country = []
  line = "."
  while(line != ""):
    line = file1.readline()
    if(line == ""):
      break
    line = line.strip("\ufeff")
    splitline = line.split(",")

    city = splitline[0]
    province = splitline[1]
    latitude = splitline[2]
    longitude = splitline[3]
    timezone = splitline[4].strip("\n")
    entry = {}
    entry["city"] = city
    entry["province/state"] = province
    entry["latitude"] = latitude
    entry["longitude"] = longitude
    entry["timezone"] = timezone
    country.append(entry)

  file1.close()
  return country

def calc_distance(coord1, coord2):
  """calculate the distance between two locations using latitudes and longtitudes"""
  return geopy.distance.distance(coord1, coord2).km 

def get_international(start_country, end_country):
    """checking if the trip is international or not (from Canada to USA and vice versa)"""
    return start_country != end_country

def get_urgency():
    """ask if the trip is urgent or not"""
    choice = input("Is the trip urgent? (Y \ N)")
    choice = choice.upper()
    while(choice != "Y" and choice != "N"):
      choice = input("Please enter a valid option.")
      choice = choice.upper()
    if(choice.upper() == "Y"):
      is_urgent = True
    else:
      is_urgent = False
    return is_urgent

def is_test():
    """ask if the current run is a test or not"""
    choice = input("Do you want to run this in test mode where you can add extra constraints? (Y \ N)")
    choice = choice.upper()
    while(choice != "Y" and choice != "N"):
      choice = input("Please enter a valid option.")
      choice = choice.upper()
    if(choice.upper() == "Y"):
      print("Running in test mode...\n")
      test = True
    else:
      print("Running normally...\n")
      test = False
    return test

def is_debug():
    """ask if the current run is a debug run"""
    choice = input("Do you want to run this in debugging mode with the default start and end point Toronto and Seattle and no urgency assumed? (Y \ N)")
    choice = choice.upper()
    while(choice != "Y" and choice != "N"):
      choice = input("Please enter a valid option.")
      choice = choice.upper()
    if(choice.upper() == "Y"):
      print("Running in debug mode...\n")
      debug = True
    else:
      print("Running normally...\n")
      debug = False
    return debug

def decide_test():
    """Get any extra constraints from the user if they are running a test."""
    print("What would you like to test? Type 'w' to test weather.\nType 'a' to test affordability.\nType 't' to test travel.")
    print("Please note that you must enter cities that cross a federal border for 'a'" + 
    " or you will get 0 solutions.")
    user_input = input()
    while(user_input.lower() not in ["w", "a", "t"]):
      user_input = input("Please enter valid input.")
    return user_input.lower()

def calc_time(distance, mode):
    """calculates the amount of time a trip would take given the mode of transportation.
    note that speed estimates are used for each mode."""
    if(mode == "drive"):
      speed = 80.0
    elif(mode == "transit"):
      speed = 200.0
    elif(mode == "plane"):
      speed = 850.0
    return distance / speed

def determine_travel_modes(drive_time, transit_time, plane_time):
    """based on the time it would take to travel from one spot to another with each mode of 
    transportation, only add reasonable modes of transportation to the travel dictionary."""
    travel = {}
    if(drive_time < 24):
        travel["drive"] = drive_time
    if(transit_time < 10):
        travel["transit"] = transit_time
    if(plane_time > 2):
        travel["plane"] = plane_time
    return travel

def raw_location_input(canada_cities, america_cities):
    """gets input of the starting city/country and ending city/country from the user"""
    start = ""
    end = ""
    inputOK = False
    # loop until the cities entered are valid and ready to be used for calculation
    while(not inputOK):
      print("When entering your cities, you can only travel to and from Canada and the United States.")
      while (not inputOK):
        start = input("Please enter your starting city, and country, separated by (just) a comma:")
        if ("," in start):
          break
      while (not inputOK):
        end = input("Please enter your ending city, and country, separated by a comma:")
        if ("," in end):
          break
      start_city = start.split(",")[0].lower()
      start_country = start.split(",")[1].lower()
      end_city = end.split(",")[0].lower()
      end_country = end.split(",")[1].lower()

      if(start_city == end_city and start_country == end_country):
        print("Your starting and ending city can't be the same.")
      elif((start_city not in canada_cities and start_city not in
      america_cities) or (end_city not in canada_cities and end_city
      not in america_cities)):
        print("You must start and end in a city in Canada or the United States.")
      elif(start_country not in ["canada", "united states"] or end_country not in ["canada", "united states"]):
        print("The country you enter must be in Canada or the United States.")
      else:
        inputOK = True

    return {"starting city":start_city, "starting country": start_country, "ending city": end_city,
    "ending country": end_country}

def clarify_duplicates(canada, america, raw_location):
    """This function asks the user to clarify their chosen city if duplicates exist."""
    duplicates_start = []
    duplicates_end = []
    inputOK = False

    raw_start_city = raw_location["starting city"]
    raw_start_country = raw_location["starting country"]
    raw_end_city = raw_location["ending city"]
    raw_end_country = raw_location["ending country"]

    #if their city is in canada, search through all the cities in canada and
    #add all the duplicates to a list
    if(raw_start_country == "canada"):
      for entry in canada:
        if(entry["city"].lower() == raw_start_city):
          duplicates_start.append(entry)
    #do the same but for american cities if their city was in the US
    else:
      for entry in america:
        if(entry["city"].lower() == raw_start_city):
          duplicates_start.append(entry)
    #repeat for the destination city
    if(raw_end_country == "united states"):
      for entry in america:
        if(entry["city"].lower() == raw_end_city):
          duplicates_end.append(entry)
    else:
      for entry in canada:
        if(entry["city"].lower() == raw_end_city):
          duplicates_end.append(entry)

    #if there are NO duplicates, the starting city is the first (original) city
    if(len(duplicates_start) == 1):
      start_city = duplicates_start[0]
    #otherwise, allow the user to pick the city they want
    else:
      print("Please enter the number beside the starting city you are referring to.") 
      for i in range(len(duplicates_start)):
        print(i)
        for value in duplicates_start[i].values():
          print(value)
        print("\n")

      while(not inputOK):
        choice = int(input("Enter your choice:"))
        if(choice > -1 and choice < len(duplicates_start)):
          inputOK = True
      start_city = duplicates_start[choice]

    #reset flag
    inputOK = False

    #do the same for the destination city
    if(len(duplicates_end) == 1):
      end_city = duplicates_end[0]
    else:
      print("Please enter the number beside the destination city you are referring to.") 
      for i in range(len(duplicates_end)):
        print(i)
        for value in duplicates_end[i].values():
          print(value)
        print("\n")
      while(not inputOK):
        choice = int(input("Enter your choice:"))
        if(choice > -1 and choice < len(duplicates_end)):
          inputOK = True
      end_city = duplicates_end[choice]

    return start_city, end_city  

def set_up_props():
    """Initializes the propositions to be used by the model"""
    #loop through all stops
    for i in range(len(stop_info)):
      #set up propositions for travel
      location = stop_info[i]["location"]
      drive[location] = transit_prop('drive from ' + location)
      transit[location] = transit_prop('take transit from ' + location)
      plane[location] = transit_prop('take a plane from ' + location)
      #set up other delay propositions
      roadwork[location]= delay_prop('roadwork happening on the path from ' + location)
      accident[location] = delay_prop('accident on the path from ' + location)
      toll[location] = delay_prop('tolls on the path from ' + location)
      #set up weather propositions
      sunny[location]= weather_prop('sunny from ' + location)
      rainy[location] = weather_prop('rainy from ' + location)
      snowstorm[location] = weather_prop('snowstorm from ' + location)

def example_theory():
    global e 

    set_up_props()

    for entry in stop_info:
      location = entry["location"]
      #exactly one weather condition must be true for each location
      constraint.add_exactly_one(e, sunny[location].name, rainy[location].name, snowstorm[location].name)

      #at most one of driving, transit, and plane propositions can be true for each location
      constraint.add_exactly_one(e, drive[location].name, transit[location].name, plane[location].name)

    #loop through each stop and set appropriate constraints
    #note: we don't necessarily set it that proposition to true unless we know 100%
    #it is true because it could still be set false by other constraints.
    #(just because something is false in one scenario, doesn't mean it's true in the 
    # opposite).
    for entry in stop_info:
      location = entry["location"]
      #if a given mode of transportation is not feasible for that trip, set the
      #constraint that it can't be true
      if "drive" not in entry["travel"].keys():
        e.add_constraint(~drive[location])
      #if it would take more than 3 hours to drive to/from this trip/the trip is international, tolls 
      #will be there
      else:
        if(entry["travel"]["drive"] > 3):
          e.add_constraint(toll[location])
          #cannot cross a toll if you have no toll money
          e.add_constraint(~((toll[location] & ~toll_money) & drive[location]))
      if "transit" not in entry["travel"].keys():
        e.add_constraint(~transit[location])
      if "plane" not in entry["travel"].keys():
        e.add_constraint(~plane[location])
      e.add_constraint(~international | toll[location])
      #at least one weather mode has to be true
      e.add_constraint(sunny[location] | rainy[location] | snowstorm[location])

      #only one form of weather can be true at once
      e.add_constraint(~sunny[location] | (~snowstorm[location] & ~rainy[location]))
      e.add_constraint(~rainy[location] | (~snowstorm[location] & ~sunny[location]))
      e.add_constraint(~snowstorm[location] | (~sunny[location] & ~rainy[location]))

      #good weather and holiday implies tickets will be sold out and you have to drive
      e.add_constraint(~(sunny[location] & holiday) | ~(transit[location] | plane[location]))
      

      #rainy or snowstorm increases the likelihood of accidents
      e.add_constraint(~(rainy[location] | snowstorm[location]) | accident[location])
      #snowstorm implies that transit and planes will be shut down
      e.add_constraint(~snowstorm[location] | ~(transit[location] | plane[location]))
      #driving constraints (come into play if they are driving):
      #bad weather and roadwork implies unfeasible trip
      e.add_constraint(~(((rainy[location] | snowstorm[location]) & roadwork[location]) & drive[location]))
      #bad weather and holiday implies unfeasible trip
      e.add_constraint(~(((rainy[location] | snowstorm[location]) & holiday) & drive[location]))
      #roadwork and holiday implies unfeasible trip
      e.add_constraint(~((roadwork[location] & holiday) & drive[location]))
      #roadwork and accident implies unfeasible trip
      e.add_constraint(~((roadwork[location] & accident[location]) & drive[location]))
      #holiday and accident implies unfeasible trip
      e.add_constraint(~((holiday & accident[location]) & drive[location]))
      #you must have at least one form of travel
      e.add_constraint(plane[location] | transit[location] | drive[location])
      #only one form of travel can be true at once
      e.add_constraint(~drive[location] | (~transit[location] & ~plane[location]))
      e.add_constraint(~transit[location] | (~drive[location] & ~plane[location]))
      e.add_constraint(~plane[location] | (~transit[location] & ~drive[location]))

      #you cannot drive anywhere if you have more than 5 people
      e.add_constraint(~more_than_five | ~drive[location])

      #you cannot take a plane if you don't have money for a ticket
      e.add_constraint(afford_plane | ~plane[location])
      
      #if you are taking an urgent trip, only the fastest trip (determined earlier) is possible
      if "drive" in entry["urgent"].keys():
        e.add_constraint(~urgent_trip  | (~transit[location] & ~plane[location]))
      elif "transit" in entry["urgent"].keys():
        e.add_constraint(~urgent_trip  | (~drive[location] & ~plane[location]))
      elif "plane" in entry["urgent"].keys():
        e.add_constraint(~urgent_trip  | (~transit[location] & ~drive[location]))
      
      #if you have the virus, you ain't flying nowhere
      e.add_constraint(~plane[location] | (~virus & documents))
      #if you don't have documents, you ain't flying nowhere
      e.add_constraint(documents | ~plane[location])

    #only relevant if travel is international
    #if you have tested positive for the virus/been in contact, you can't cross the border
    e.add_constraint(~international | (~virus & documents))
    #no documents means you can't cross the border
    e.add_constraint((international & documents) | ~international)

    return e    

def test_weather(stop_info):
    """Tests weather constraints by adding more weather constraints to the list of extra test constraints
    to be used with this run."""
    extra_con = []
    set_up_props()
    for entry in stop_info:
      location = entry["location"]
      #ensure that it is not a snowstorm so transit could always happen
      extra_con.append(~snowstorm[location])
      #ensure that a holiday and taking the train means that it is NOT sunny
      extra_con.append(transit[location] & holiday)
      #the above two implies it will be rainy, which will imply accidents
      #should fail the model due to a contradiction
      extra_con.append(~accident[location])
    return extra_con

def test_affordability():
    """Tests affordability constraints."""
    extra_con = []
    set_up_props()
    for entry in stop_info:
      location = entry["location"]
      #force international to be true so there will be toll money
      extra_con.append(international)
      #force plane to be false
      extra_con.append(~afford_plane)
      #forced the driver to have no toll money
      extra_con.append(~toll_money)
      #(either transit will always be true or the model will fail). The below will fail the model.
      extra_con.append(~transit[location])
    return extra_con

def test_travel():
    """Tests travel constraints."""
    extra_con = []
    set_up_props()
    for entry in stop_info:
      location = entry["location"]
      #force more than five people to take the trip (negates driving)
      extra_con.append(more_than_five)

      #force one of them to have COVID (cannot take a plane/travel internationally)
      #if the user enters an international trip there should be 0 solutions.
      #in other words, their only option in this scenario is to take transit domestically.
      #negating transit gives us 0 solutions then, of course.
      extra_con.append(virus)
      extra_con.append(~transit[location])
    return extra_con  

def solve(border, is_urgent, test, extra_con=[]):
    """Sets up and uses the SAT solver."""
    #set up the solver
    T = example_theory()

    #account for international status/urgency
    if(border):
      T.add_constraint(international)
      print("This trip is international...")
    else:
      T.add_constraint(~international)
      print("This trip is not international...")

    #add more constraints if the trip is urgent
    if(is_urgent):
      T.add_constraint(urgent_trip)
    else:
      T.add_constraint(~urgent_trip)

    if test:
      #add any extra constraints
      if extra_con != []:
        for constraint in extra_con:
          T.add_constraint(constraint)

    #get NNF object
    T = T.compile()

    print("\nSatisfiable: %s" % T.is_satisfiable())
    print("# Solutions: %d" % T.count_solutions())
    print("   Solution: %s" % T.solve())

def main():
    """Runs the program."""

    #ask the user if they are running in debug mode
    debug = is_debug()

    #normal mode - get locations from user
    if not debug:
      #ask the user if a test is being run
      test = is_test()
      #if it is a test, get any extra constraints from the user
      if test:
        type_of_test = decide_test()

      #will store extra constraints if a test is being run
      extra_con = []

      #read in the databases (each database contains the city name and its 
      #longitude/latitude coordinate).
      canada = read_files("canada", "Canada Cities.csv")
      america = read_files("america", "US Cities.csv")

      # create a list for canadian and american cities
      canada_cities = []
      america_cities = []
      for entry in canada:
        canada_cities.append(entry["city"].lower())
      for entry in america:
        america_cities.append(entry["city"].lower())    

      #get the raw location from the user and clarify any duplicates to get the
      #starting and ending city (the countries will of course remain the same)
      raw_location = raw_location_input(canada_cities,america_cities)
      start_city, end_city = clarify_duplicates(canada, america, raw_location)
      start_country = raw_location["starting country"]
      end_country = raw_location["ending country"]

      is_urgent = get_urgency()

      #calculate the total distance between the starting and ending city
      start_coord = (start_city["latitude"], start_city["longitude"])
      end_coord = (end_city["latitude"], end_city["longitude"])
      total_dist = calc_distance(start_coord, end_coord)

      print(str(start_coord) + " " + str(end_coord))

      #tell the user the total number of km
      print("A trip from " + start_city["city"] + ", " + start_city["province/state"] + " to " + end_city["city"]
      + ", " + end_city["province/state"] + " is " + str(total_dist)+ " km long.")

      #calculate 1/tenth of the distance from the start to the end
      #the user will be given 10 choices of evenly spaced cities to stop at along the way 
      #they can stop at 0, 1, or multiple; their choice
      next_dist = total_dist/10
    
      geodesic = pyproj.Geod(ellps='WGS84')
      #calculates the initial bearing (fwd_azimuth) and the final bearing 
      fwd_azimuth,back_azimuth,distance = geodesic.inv(start_city["longitude"], start_city["latitude"], end_city["longitude"], end_city["latitude"])
      final_bearing = back_azimuth - 180

      #Define the starting and ending points.
      temp_start = geopy.Point(start_city["latitude"], start_city["longitude"])
      end = geopy.Point(end_city["latitude"], end_city["longitude"])
      start = temp_start

      #Define a general distance object, initialized with a distance of the stop distance (in km).
      d = geopy.distance.distance(kilometers=next_dist)

      #lists that will hold all the stops and the stops that the user chooses, respectively
      all_stops = []
      chosen_stops = []

      #define the geolocator
      geolocator = Nominatim(user_agent="Bing")

      #loop 10 times (for 10 stops)
      for i in range(10):
        # Use the destination method with our starting point and initial bearing
        # in order to go from our starting point to the next city in the line of stops.
        #finds the next point from the starting point given the bearing
        #if we are closer to the start, use our initial bearing; otherwise, use the final bearing
        if(i < 5):
          final = d.destination(point=temp_start, bearing=fwd_azimuth)
        else:
          final = d.destination(point=temp_start, bearing=final_bearing)
        
        #finds the location 
        location = geolocator.reverse(str(final))
        print(str(i) + ": " + str(location))
        #add it to the list of all stops
        all_stops.append({"location":str(location),"coord":final})
        #reset the next starting point
        temp_start = final

      #add the starting location to the chosen stops
      chosen_stops.append({"location": start_city["city"], "coord": start})

      user_input = -2 #initizalize
      #get the user input for the stops they would like and store it in chosen_stops
      print("Please enter which stops you would like to take along the way." + 
      "If you are done entering stops, please enter '-1'. If you don't want to take any stops," +
      " enter -1 right away.")
      while(user_input != -1):
        user_input = int(input("Enter your next stop: "))
        if (user_input < -1 or user_input > 9):
            print("Wrong input! Please try again!")
        else:    
          if (user_input != -1):
            chosen_stops.append(all_stops[user_input])


      #add the ending location to the chosen stops
      #chosen_stops is now a list of all stops including the start and end
      chosen_stops.append({"location": end_city["city"], "coord": end})

      #add constraints for the appropriate test, if it is a test
      if test:
        if type_of_test == "w":
          extra_con = test_weather(stop_info)
        elif type_of_test == "a":
          extra_con = test_affordability()
        elif type_of_test == "t":
          extra_con = test_travel()
    else:
      #debugging mode - default start and stop
      chosen_stops = []
      chosen_stops.append({"location": "Toronto, Canada", "coord": ('43.7417', '-79.3733')})
      chosen_stops.append({"location": "Seattle, United States", "coord": ('47.6211', '-122.3244')})
      start_country = "canada"
      end_country = "united states"
      is_urgent = False
      test = False
      extra_con = []


    for i in range(len(chosen_stops) - 1):
      #calculate the distance between each stop
      distance = calc_distance(chosen_stops[i]["coord"], chosen_stops[i + 1]["coord"])
      print("The distance between " + str(chosen_stops[i]["location"]) + " and " + 
      str(chosen_stops[i + 1]["location"]) + " is " + str(distance) + " km. ")
      dict_string = str(chosen_stops[i]["location"]) + " to " + str(chosen_stops[i+1]["location"])
      #set up the dictionary and append it to the list
      entry = {"location": dict_string, "distance" : distance}
      stop_info.append(entry)

    #loop through every stop 
    for i in range(len(stop_info)):
      #now that we know the distance, we can calculate the time needed to travel
      #between each stop with each mode of transportation
      distance = stop_info[i]["distance"]
      drive_time = calc_time(distance, "drive")
      transit_time = calc_time(distance, "transit")
      plane_time = calc_time(distance, "plane")
      travel = determine_travel_modes(drive_time, transit_time, plane_time)

      for mode in travel:
        print(mode + " from " + stop_info[i]["location"] + ":" + str(travel[mode]) + " hours.")

      all_modes = []
      urgent = {}
      #determine the FASTEST mode of travel
      if travel != {}:
        if "drive" in travel.keys():
          all_modes.append(travel["drive"])
        if "transit" in travel.keys():
          all_modes.append(travel["transit"])
        if "plane" in travel.keys():
          all_modes.append(travel["plane"])
      fastest = min(all_modes)
      for mode in travel:
        if travel[mode] <= fastest:
          urgent[mode] = travel[mode]
      
      #add a new key, the dictionary of available travel modes, to the list
      stop_info[i]["travel"] = travel
      #do the same with the urgent travel mode
      stop_info[i]["urgent"] = urgent

      #reset the travel modes
      travel = {}
      urgent = {}

    #determine if the travel is international or not and set the appropriate constraint
    border = get_international(start_country, end_country)

    #solve!
    solve(border, is_urgent, test, extra_con)

main()

#if __name__ == "__main__":