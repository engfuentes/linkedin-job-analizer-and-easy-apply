# linkedin-easy-apply

## Project that checks in Linkedin (using NLP) if you have the Language, Experience and Technology requirements for a chosen position and country. If you have them, it applies using EasyApply.

The user can choose different options in *configfile.ini* 

*Playwright* framework is used to search for a position and country and applies a filter to find the jobs that have *"EasyApply"*. Then scraps each job position of the list and afer perform the following tasks:
- If the job description is in other language than in English it translates it with the *googletrans* library.
- Cleans the job description.
- Analyze job descriptions with spaCy, an NLP (Natural Language Processing) library.

With the options that you choose in the configfile.ini it will decide if you should apply to the position or not based on the language you are fluent, your experience and the technologies that you know.
The apply decision is recorded to the job instance together with the reasons not to apply to the job and a list of word tags that are present in the description.

The words that spaCy check are entities that are in *./data/data.json*. They were added in the context of an IT job search.

If *easy_apply = True* in *configfile.ini* then it applies for the position. It has a dictionary in *data/easy_apply_questions_answers.json* with the EasyApply questions and answers. When it has to answer and it doesn't find an answer it saves the missing questions in another json file in ./data folder.

The webscrapped data can be saved to a json file and/or to a PostgreSQL Database

## Steps to use it

1- Create a virtual environment for example with pipenv. Open the terminal and write:

    pipenv shell
    pipenv install -r requirements.txt

2- Install the playwright browsers:

    playwright install

3- Download spaCy large NLP model:

    python -m spacy download en_core_web_lg 

4- Generate cookies to login to linkedin:

Run the following code:

    playwright codegen linkedin.com --save-storage=auth.json

Login manually to linkedin in the browser. After login close the browser, it will save all the information to a file *auth.json*. **DON'T SHARE THIS FILE** (I added to the gitignore file of the repo).

5- Choose the options that you want and the words to use in spaCy in *configfile.ini*

6- If you choose to use a PostgreSQL Database create a .env file with the required env variables:

    POSTGRESQL_HOSTNAME = 'localhost'
    POSTGRESQL_USERNAME = "username"
    POSTGRESQL_PASSWORD = 'password'
    POSTGRESQL_DATABASE = 'db_name'

7- Run in the terminal to run the script:

    python linkedin_easy_apply.py