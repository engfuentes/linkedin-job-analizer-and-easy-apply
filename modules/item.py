class Job():
    def __init__(self):
        self.search_position = None
        self.search_country = None
        self.url = None
        self.position_name = None
        self.company = None
        self.country = None
        self.city = None
        self.contract_type = None
        self.applicants = None
        self.contract_time = None
        self.experience = None
        self.description = None
        self.posted_date = None
        self.apply = None
        self.email = None
        self.reason_not_apply = None
        self.list_tech_no_knowledge = None
        self.list_tags = None
        self.easy_apply_questions = None
        self.applied = None
        self.could_not_apply_due_to_questions = None
    
    def transform_to_dict(self):
        return self.__dict__