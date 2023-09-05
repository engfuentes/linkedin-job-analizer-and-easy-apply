class Job():
    def __init__(self):
        self.url = None
        self.name = None
        self.company = None
        self.location = None
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
    
    def transform_to_dict(self):
        return self.__dict__