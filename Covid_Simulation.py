#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Aug 28 14:49:23 2020

@author: geoff

DESCRIPTION
Simulation models 2 young kids (siblings) in two different schools.
Once school does Covid testing, the other school does not. 
The major questions to answer are:
1) The chance that either of them is infected with Covid
2) If one is infected, is there sufficient warning 
before a direct contact (e.g., grandparent) is infected?
3) If one is infected, is there sufficient warning
before a 2nd degree contact (e.g., cousin) is infected? 

ASSUMPTIONS 
* complete and certain spread within classrooms
once anyone is contagious
* complete and certain spread within families
once anyone is contagious
* for other assumptions, see the settings 
of the constants below


PRELIMINARY RESULTS
73% chance that at least one kid is infected in 90 days
57%  chance that at least one kid is 
infected and there is sufficient warning for the direct contact
2%  chance that at least one kid is infected and
there is only sufficient warning for the second-degree contact
14%  chance that at least one kid is infected and
there is no warning even for the second-degree contact

Almost all the danger of infection without warning is
from the school that does not test


TODO
Model warnings from symptoms.  Here age comes into play
Model spread between classrooms other than family spread
Model immunity in the community.  
Perhaps 6,000 people already immune in the town?

Exceptions instead of 'Error'

Assert
everyone belongs to family unit

"""
import math
import random

population = 30054 # for local town of schools
cases_in_aug = 7 # town-wide cases
undetected_per_detected = 10 # https://jamanetwork.com/journals/jamainternalmedicine/fullarticle/2768834
actual_cases_in_aug = cases_in_aug*(undetected_per_detected+1)

test_lag = 1 # days to get test results
first_contagious_day = 3
last_contagious_day = 13

first_positive_test_day = 1
last_positive_test_day = 16

students_per_family = 1.25

S1_class_size = 14
S1_teachers = 2
S1_classes_in_school = 10

S2_class_size = 10
S2_teachers = 2
S2_classes_in_school = 3

N_sim = 1000
N_days = 90

class person:
    def __init__(self, name, age):
        self.name = name
        self.age = age
        self.days_with_virus = -1
        self.day_infected = 1000000
        self.family_unit = None 
        #self.would_show_symptoms = would_show_symptoms
        
    def assign_to_family(self, fam):
        self.family_unit = fam

    def is_sick(self):
        if self.days_with_virus > -1:
            return True
        else:
            return False
        
    def tests_positive(self):
        #According to
        #https://files.constantcontact.com/340b0174501/3f8891bd-72ab-4784-8f79-95d1314ead01.pdf 
        #There is high RNA generally within 1-2 days 
        #after the initial infection.
        if ((self.days_with_virus > first_positive_test_day) and
            (self.days_with_virus <= last_positive_test_day)):
            return True
        else:
            return False

    def is_contagious(self):
        if ((self.days_with_virus >= first_contagious_day) and
            (self.days_with_virus < last_contagious_day)):
            return True
        else:
            return False
            
    def sicken(self, day):
        if self.days_with_virus == -1:
            self.days_with_virus = 0
            self.day_infected = day
            
    def update_days_sick(self):
        if self.days_with_virus != -1:
            self.days_with_virus += 1
        

class classroom:
    def __init__(self, number, class_size, age, num_teachers):
        self.number = number # id for classroom
        self.students = [
                person("student_" + str(number) + "_" + str(i),
                       age)
                for i in range(class_size)]
        self.teachers = [
                person("teacher_" + str(number) + "_" + str(i),
                       30)
                for i in range(num_teachers)]

        self.earliest_positive_test_day = None
        

    def assign_to_families(self, fam_assignments):
        for stdt in self.students:
            fam = fam_assignments.pop(0)
            stdt.assign_to_family(fam)

    def any_contagious_cases_in_classroom(self):
        any_cases = False
        for stdt in self.students:
            if stdt.is_contagious():
                any_cases = True
        for teach in self.teachers:
            if teach.is_contagious():
                any_cases = True
        return any_cases

    def num_contagious_students_in_classroom(self):
        num_contagious = 0
        for stdt in self.students:
            if stdt.is_contagious():
                num_contagious += 1
        return num_contagious

    def sicken_all(self, day):
        # sickens everyone who doesn't have virus already
        for stdt in self.students:
            stdt.sicken(day)
        for teach in self.teachers:
            teach.sicken(day)
            
    def update_days_sick(self):
        for stdt in self.students:
            stdt.update_days_sick()
        for teach in self.teachers:
            teach.update_days_sick()

    def test(self, day):
        for stdt in self.students:
            if stdt.tests_positive():
                if self.earliest_positive_test_day is None:
                    self.earliest_positive_test_day = day
                
    def offline(self, day):
        # classroom taken offline when there is positive test
        if self.earliest_positive_test_day is None:
            return False
        elif day > self.earliest_positive_test_day + test_lag:
            return True
        else:
            return False

class school: 
    def __init__(self, name, num_classrooms,
                 class_size, ages_list, teachers_per_class):
        # ages_list has one age for each classroom 
        # all students in a classroom assumed to be same age
        
        self.name = name # name of school
        
        self.classrooms = [
                classroom(i+1, class_size, ages_list[i],
                          teachers_per_class)
                for i in range(num_classrooms)
                ]
        
        self.class_size = class_size
        
    def test(self, day):
        for clrm in self.classrooms:
            clrm.test(day)
                    
    def actual_students_per_family(self):
        family_set = set()
        num_students = 0
        for clrm in self.classrooms:
            for stdt in clrm.students:
                family_set.add(stdt.family_unit)
                num_students += 1
        return num_students/len(family_set)

    def assign_to_random_families(self):
        
        if students_per_family < 1:
            print ("Can't have fewer than 1 student per family.")
            return
       
        num_families = math.floor(
                self.total_students()/students_per_family)
        fam_assignments = list(range(num_families))
        
        for i in range(self.total_students() - num_families):
            fam_assignments.append(random.randint(0, num_families-1))
        
        random.shuffle(fam_assignments)
        for clrm in self.classrooms:
            clrm.assign_to_families(fam_assignments[0:self.class_size])
            del fam_assignments[0:self.class_size]

    def spread_virus(self, day):
        # spread virus 

        #within classrooms, only on weekdays
        #and only if classroom is not offline 
        #(i.e., has positive test results)
        if not ((day % 7) in [5, 6]):
            for clrm in self.classrooms:
                if (not clrm.offline(day)):
                    if clrm.any_contagious_cases_in_classroom():
                        clrm.sicken_all(day)
                    
        # TODO - spread between classrooms (e.g., bathrooms, busses)
        
        #within families
        contagious_families = set()
        for clrm in self.classrooms:
            for stdt in clrm.students:
                if stdt.is_contagious():
                    contagious_families.add(stdt.family_unit)

        for clrm in self.classrooms:
            for stdt in clrm.students:
                if stdt.family_unit in contagious_families:
                    stdt.sicken(day)
                    
    def total_people(self):
        # returns total people in the school
        # includes teachers and students only (no admins)
        total = 0
        for clrm in self.classrooms:
            total += len(clrm.students) + len(clrm.teachers)
        return total

    def total_students(self):
        # returns total students in the school
        total = 0
        for clrm in self.classrooms:
            total += len(clrm.students)
        return total

    def total_students_contagious(self):
        # returns total students contagious in school
        # (We assume only students spread the virus to other
        # classrooms, via busses and siblings)
        total = 0
        for clrm in self.classrooms:
            total += clrm.num_contagious_students_in_classroom()
        return total

    def update_days_sick(self):
        # For sick people, increments days_with_virus
        for clrm in self.classrooms:
            clrm.update_days_sick()

    def any_school_cases(self):
        # Returns true if any cases in the school
        any_cases = False
        for clrm in self.classrooms:
            for stdt in clrm.students:
                if stdt.is_sick():
                    any_cases = True
                
            for teach in clrm.teachers:
                if teach.is_sick():
                    any_cases = True
                    
        return any_cases

    def any_contagious_cases_in_classroom(self, classrm):
        # Returns true if any cases in classrm
        any_cases = False
        for clrm in self.classrooms:
            if clrm.number == classrm:
                any_cases = clrm.any_contagious_cases_in_classroom()
        return any_cases

    def sicken_xth_person(self, x, exclude_list, day):
        # makes xth person sick and returns True if 
        # not excluded and not already sick
        # (we don't sicken anyone on exclude_list)
        # first person in school is person 0
        # else returns False
        p = -1
        for clrm in self.classrooms:
            for stdt in clrm.students:
                p += 1
                if p == x:
                    if stdt.name in exclude_list:
                        return False
                    if stdt.is_sick():
                        return False
                    else:
                        stdt.sicken(day)
                        return True
                
            for teach in clrm.teachers:
                p += 1
                if p == x:
                    if teach.name in exclude_list:
                        return False
                    if teach.is_sick():
                        return False
                    else:
                        teach.sicken(day)
                        return True

        print ("Error - there are not {} applicable people in school".format(x))
    

def resident_cases(residents):
    num_cases = 0
    for i in residents:
        if i.is_sick():
            num_cases += 1
    return num_cases


# In what pct of simulations does S1 or S2 get virus?
new_cases_per_day = actual_cases_in_aug/30
fraction_part = new_cases_per_day % 1

S1_infections = 0
S2_infections = 0
S1_infections_no_warning = 0
S1_infections_some_warning = 0 # in time to save 2nd degree of separation
S1_infections_good_warning = 0 # in time to save 1st degree of separation

Agg_infections = 0
Agg_infections_no_warning = 0
Agg_infections_some_warning = 0
Agg_infections_good_warning = 0

def determine_agg_warnings(
    earliest_positive_test_day,
    day_contagious,
    Agg_infections_no_warning,
    Agg_infections_some_warning,
    Agg_infections_good_warning
    ):
    if earliest_positive_test_day is None:
        Agg_infections_no_warning += 1
                  
    elif earliest_positive_test_day\
        + test_lag >= day_contagious + first_contagious_day:
        Agg_infections_no_warning += 1
            
    elif earliest_positive_test_day\
        + test_lag >= day_contagious:
        Agg_infections_some_warning += 1

    else: 
        Agg_infections_good_warning += 1 

    return (Agg_infections_no_warning,
            Agg_infections_some_warning,
            Agg_infections_good_warning)


for sim in range(N_sim):
    print ("Sim: {}".format(sim))
    #init people

    S1_school = school("S1_school", S1_classes_in_school,
                      S1_class_size, [5]*S1_class_size, S1_teachers)

    S2_school = school("S2_school", S2_classes_in_school,
                      S2_class_size, [3]*S2_class_size, S2_teachers)
    
    other_residents = [
        person("resident" + str(i), 30)
        for i in range(population
                       -S1_school.total_people()
                       -S2_school.total_people())] 

    # assign students to families
    S1_school.assign_to_random_families()
    S2_school.assign_to_random_families()
    
    # but put our two siblings of interest in their own family.
    # Or separate families if we want to tease apart 
    # the influence of either school
    S1_school.classrooms[0].students[0].assign_to_family(-1)
    S2_school.classrooms[0].students[0].assign_to_family(-2)
    
    for day in range (N_days+2*first_contagious_day):
        
        #update days sick
        for resident in other_residents:
            resident.update_days_sick()
        
        S1_school.update_days_sick()
        S2_school.update_days_sick()
        
        #assign new cases of sickness (i.e., originating outside 
        #the town)
        if random.uniform(0, 1) < fraction_part:
            today_cases = math.ceil(new_cases_per_day)
        else:
            today_cases = math.floor(new_cases_per_day)
        
        if today_cases > 0:
            #print ("Cases today: {}".format(today_cases))
            pop = list(range(population)) 
     
            new_list = random.sample(pop, today_cases) 
            for i in new_list:
                if i < len(other_residents):
                    other_residents[i].sicken(day)
                elif i < len(other_residents) + S1_school.total_people(): 
                    already_sick = not S1_school.sicken_xth_person(
                            i-len(other_residents), "student_1_1", day)

                else: 
                    already_sick = not S2_school.sicken_xth_person(
                            i-len(other_residents)-S1_school.total_people(),
                            "student_1_1", day)
    
        
        #spread virus from existing cases in schools
        S1_school.spread_virus(day)
        S2_school.spread_virus(day)
        
        #test for virus - only on certain days
        #if True:
        if (day % 7 in [0, 2]):
            S1_school.test(day)
            #S2_school.test(day) # No testing at S2_school
        

    #Final results for simulation
    if S1_school.classrooms[0].students[0].day_infected <=\
        N_days:
            
        S1_infections += 1 
        
        day_contagious =\
            S1_school.classrooms[0].students[0].day_infected +\
            first_contagious_day
        
        if S1_school.classrooms[0].earliest_positive_test_day\
        is None:
            S1_infections_no_warning += 1

        elif S1_school.classrooms[0].earliest_positive_test_day\
        + test_lag >= day_contagious + first_contagious_day:
            S1_infections_no_warning += 1
            
        elif S1_school.classrooms[0].earliest_positive_test_day\
        + test_lag >= day_contagious:
            S1_infections_some_warning += 1

        else: 
            S1_infections_good_warning += 1 
        
    if S2_school.classrooms[0].students[0].day_infected <=\
        N_days:
            
        S2_infections += 1        

    if ((S1_school.classrooms[0].students[0].day_infected <=\
        N_days) or
        (S2_school.classrooms[0].students[0].day_infected <=\
        N_days)):
        Agg_infections += 1 

    # Aggregate warnings must account for joint occurrences
    # at both schools.  E.g.,  there might be an infection 
    # at school 2, and we luck out with a 
    # timely (unrelated) warning at school 1

    if ((S1_school.classrooms[0].students[0].day_infected <=\
         N_days) and
        (S2_school.classrooms[0].students[0].day_infected <=\
         N_days)   
        ):
        day_contagious = min(\
            S1_school.classrooms[0].students[0].day_infected +\
            first_contagious_day, 
            S2_school.classrooms[0].students[0].day_infected +\
            first_contagious_day) 
          
        (Agg_infections_no_warning,
            Agg_infections_some_warning,
            Agg_infections_good_warning) =\
        determine_agg_warnings(
            S1_school.classrooms[0].earliest_positive_test_day,
            day_contagious,
            Agg_infections_no_warning,
            Agg_infections_some_warning,
            Agg_infections_good_warning)
 
    elif (S1_school.classrooms[0].students[0].day_infected <=\
         N_days):
        day_contagious =\
            S1_school.classrooms[0].students[0].day_infected +\
            first_contagious_day 
          
        (Agg_infections_no_warning,
            Agg_infections_some_warning,
            Agg_infections_good_warning) =\
        determine_agg_warnings(
            S1_school.classrooms[0].earliest_positive_test_day,
            day_contagious,
            Agg_infections_no_warning,
            Agg_infections_some_warning,
            Agg_infections_good_warning)

    elif (S2_school.classrooms[0].students[0].day_infected <=\
         N_days):
        day_contagious =\
            S2_school.classrooms[0].students[0].day_infected +\
            first_contagious_day 
          
        (Agg_infections_no_warning,
            Agg_infections_some_warning,
            Agg_infections_good_warning) =\
        determine_agg_warnings(
            S1_school.classrooms[0].earliest_positive_test_day,
            day_contagious,
            Agg_infections_no_warning,
            Agg_infections_some_warning,
            Agg_infections_good_warning)


    #print ("resident_cases: {}".format(resident_cases(other_residents)))
    
print ("Infection rate (S1): {}".format(S1_infections/N_sim))
print ("Inf rate, no warning (S1): {}".format(S1_infections_no_warning/N_sim))
print ("Inf rate, some warning (S1): {}".format(S1_infections_some_warning/N_sim))
print ("Inf rate, good warning (S1): {}".format(S1_infections_good_warning/N_sim))
print ("\n")
print ("Infection rate (S2): {}".format(S2_infections/N_sim)) 
print ("\n")
print ("AGGREGATE RESULTS:")
print ("Infection rate (any): {}".format(Agg_infections/N_sim))
print ("Inf rate, no warning: {}".format(Agg_infections_no_warning/N_sim))
print ("Inf rate, some warning: {}".format(Agg_infections_some_warning/N_sim))
print ("Inf rate, good warning: {}".format(Agg_infections_good_warning/N_sim))
