import json
from bs4 import BeautifulSoup

INPUT_FILE_NAME = 'source.html'
OUTPUT_FILE_NAME = 'data-v40.json'
OUTPUT_FILE_NAME_MIN = 'data-v40.min.json'


def map_time_to_blocks(time_string):
    time_blocks = time_string.split(' - ')
    start_time = time_blocks[0]
    end_time = time_blocks[1]

    # 8:40 is 0 and it goes on from there
    start_time_blocks = start_time.split(':')[0]
    end_time_blocks = end_time.split(':')[0]

    #do the mapping
    start_time_blocks = int(start_time_blocks) - 8
    end_time_blocks = int(end_time_blocks) - 8

    if start_time_blocks < 0:
        start_time_blocks += 12
        end_time_blocks += 12

    duration = end_time_blocks - start_time_blocks

    return start_time_blocks, duration

def map_day_to_blocks(day_string):
    day_string = day_string.strip()
    if day_string == 'M':
        return 0
    elif day_string == 'T':
        return 1
    elif day_string == 'W':
        return 2
    elif day_string == 'R':
        return 3
    elif day_string == 'F':
        return 4
    elif day_string == 'S':
        return 5
    elif day_string == 'U':
        return 6
    else:
        return -1

def map_faculty_to_acronym(faculty_string):
    fac = ""
    if 'Arts' in faculty_string:
        fac =  "FASS"
    elif 'Business' in faculty_string:
        fac =  "FMAN"
    elif 'Engin' in faculty_string:
        fac =  "FENS"
    elif 'Languages' in faculty_string:
        fac = "SL"
    else:
        fac =  "TBA"

    place = faculty_string.split(' ')[-1]

    location = fac + " " + place
    return location

def insert_place_to_places(place, places):
    """
    Insert a place to the places set, and return its index, if it already exists, return its index
    """
    if place in places:
        return places.index(place)
    else:
        places.append(place)
        return len(places) - 1

def insert_instructor_into_instructors(instructor, instructors):
    """
    Insert an instructor to the instructors set, and return its index, if it already exists, return its index
    """
    if instructor in instructors:
        return instructors.index(instructor)
    else:
        instructors.append(instructor)
        return len(instructors) - 1

def insert_course_into_courses(course, courses):
    """
    Insert a course to the courses set, and return its index, if it already exists, return its index
    """
    if course in courses:
        return courses.index(course)
    else:
        courses.append(course)
        return len(courses) - 1

def find_course_by_name(name, courses):
    for course in courses:
        if course['name'] == name:
            return courses.index(course)
    return None

def find_course_by_code(code, courses):
    for course in courses:
        if course['code'] == code:
            return courses.index(course)
    return None

def get_course_type_and_code(code):
    #if the course code does not end with a number
    if not code[-1].isdigit():
        return code[-1], code[:-1]
    else:
        return '', code


with open(INPUT_FILE_NAME, 'r') as file:
    html_content = file.read()

soup = BeautifulSoup(html_content, 'html.parser')

courses = []
places = []
instructors = []

new_json_data = {"courses": [],
                 "instructors": [],
                 "places": []}

course_blocks = soup.find_all('th', class_='ddlabel')

print("course_blocks: ", len(course_blocks))
print("first course_block: ", course_blocks[0].text)

#course_blocks = course_blocks[0:2]

for course_block in course_blocks:
    info = course_block.text.split(' - ')

    if len(info) < 4:
        continue

    # check if the second place is crn, if not, remove it
    try:
        crn = int(info[1])
    except:
        info = info[0:1] + info[2:]
        #print("corrected info: ", info)

    name = info[0]
    crn = info[1]
    code = info[2]
    section = info[3] #group

    print('name', name, 'crn', crn, 'code', code, 'section', section)

    # find associated course details
    parent_row = course_block.find_next("tr")
    schedule_table = parent_row.find("table", class_="datadisplaytable")

    course_type ,code = get_course_type_and_code(code)

    instructors_index = -1
    
    schedule_entries = []
    if schedule_table:
        for schedule_row in schedule_table.find_all("tr")[1:]:  # Skip header row
            cells = schedule_row.find_all("td")

            if len(cells) < 3:
                continue

            # Getting data into the proper format -------------------------
            try:
                start_time, duration = map_time_to_blocks(cells[1].text.strip())
            except:
                start_time, duration = -1, -1

            day = map_day_to_blocks(cells[2].text.strip())

            place = map_faculty_to_acronym(cells[3].text.strip())
            place_index = insert_place_to_places(place, places)

            instructors_index = insert_instructor_into_instructors(cells[6].text.strip(), instructors)
            # done -------------------------------------------------------

            schedule_entries.append({
                "day": day, 
                "place": place_index,
                "start": start_time,
                "duration": duration
            })

    #create this course object
    course = {
        "name": name,
        "code": code,
        "classes": [{
            "type": course_type,
            "sections": [{
                "crn": crn,
                "schedule": schedule_entries,
                "group": section,
                "instructors": instructors_index
            }]
        }]
    }

    #course_index = find_course_by_name(name, courses)
    course_index = find_course_by_code(code, courses)
    if course_index is not None:
        #If class is a recitation or lab, its a different class, if different secion, then its under sections
        course = courses[course_index]

        #check if our type is already there, add section
        found = False
        for course_class in course['classes']:
            if course_class['type'] == course_type:
                found = True
                section = {
                    "crn": crn,
                    "schedule": schedule_entries,
                    "group": section,
                    "instructors": instructors_index
                }
                course_class['sections'].append(section)
                break

        # if not found, add the class with the section
        if not found:
            course['classes'].append({
                "type": course_type,
                "sections": [{
                    "crn": crn,
                    "schedule": schedule_entries,
                    "group": section,
                    "instructors": instructors_index
                }]
            })
    else:
        #There is no course with this name, add it to the courses
        courses.append(course)

# Add the courses, places and instructors to the new_json_data
new_json_data["courses"] = courses
new_json_data["places"] = places
new_json_data["instructors"] = instructors

# Save the processed JSON
with open(OUTPUT_FILE_NAME, "w", encoding="utf-8") as file:
    json.dump(new_json_data, file, ensure_ascii=False, indent=2)

# Save into minified JSON
with open(OUTPUT_FILE_NAME_MIN, "w", encoding="utf-8") as file:
    json.dump(new_json_data, file, ensure_ascii=False, separators=(',', ':'))
