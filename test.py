class LivingBeing:
    species = "Unknown"

class Dog(LivingBeing):
    species = "Canine"

    def __init__(self, name, age):
        self.name = name
        self.age = age

class Person(LivingBeing):
    species = "Homo Sapiens"

    def __init__(self, name, age):
        self.name = name
        self.age = age

class Worker:
    def __init__(self, job_title):
        self.job_title = job_title

class Employee(Person, Worker):
    def __init__(self, name, age, employee_id, job_title):
        Person.__init__(self, name, age)
        Worker.__init__(self, job_title)
        self.employee_id = employee_id

class Manager(Employee):
    def __init__(self, name, age, employee_id, department, job_title):
        super().__init__(name, age, employee_id, job_title)
        self.department = department

class Student(Person):
    def __init__(self, name, age, roll_no):
        super().__init__(name, age)
        self.roll_no = roll_no

student1 = Student("Alice", 20, "S123")
student2 = Student("Bob", 22, "S456")

print(student1.species)
print(student1.name)  
print(student1.age)      
print(student1.roll_no)  

print(student2.species)  
print(student2.name)    
print(student2.age)      
print(student2.roll_no)  

student1.name = "Charlie"
print(student1.name)

Person.species = "Homo Sapiens"
print(student1.species)  
print(student2.species)  

dog1 = Dog("Buddy", 3)
dog2 = Dog("Charlie", 5)

print(dog1.species)  
print(dog1.name)     
print(dog2.name)    

dog1.name = "Max"
print(dog1.name)

Dog.species = "Feline"
print(dog1.species)  
print(dog2.species)  

manager = Manager("Alice", 30, "M123", "HR", "HR Manager")

print(manager.name)        
print(manager.age)         
print(manager.employee_id) 
print(manager.department)
print(manager.job_title)
