import asyncio, logging
from playwright.async_api import async_playwright
from modules.helper_functions import scrap_job, log_exceptions, check_easy_apply_button
from modules.check_apply import check_apply_or_not
from modules.easy_apply import easy_apply

async def create_broswer_page(p, dict_user_opts):
    """Function that creates a broswer, context and page.
    
    Parameters
    ----------
        p : playwright object
            playwright object
        dict_user_opts : dict
            Dictionary with the user options of search, save and apply

    Returns
    -------
        page : playwright object
            playwright page object
        browser : playwright object
            playwright browser object
        context : playwright object
            playwright context object
    """
    # Create browser
    browser = await p.chromium.launch(headless=dict_user_opts["headless"])
    
    # Create a context and load the cookies with the login info
    context = await browser.new_context(storage_state="auth.json")
    
    # Enter to linkedin
    page = await context.new_page()
    
    await page.goto("https://www.linkedin.com/jobs/")

    return page, browser, context

async def search_job_position(page, user_search_position):
    """Function to search for the job position

    Parameters
    ----------
        page : playwright object
            playwright page object
        user_search_position : str
            Position to search for

    Returns
    -------
        page : playwright object
            playwright page object
    """
    # Choose the job title
    await page.get_by_role("combobox", name="Search by title, skill, or company").fill(f'{user_search_position}')
    await page.wait_for_timeout(1000)
    await page.locator("label", has_text="Search by title, skill, or company").press("Enter") # 
    await page.wait_for_timeout(1000)

    return page

async def search_job_country(page, user_search_country):
    """Function to search for the job country

    Parameters
    ----------
        page : playwright object
            playwright page object
        user_search_country : str
            Country to search for

    Returns
    -------
        page : playwright object
            playwright page object
    """
    # Choose the country
    await page.get_by_role("combobox", name="City, state, or zip code").fill(f'{user_search_country}')
    await page.wait_for_timeout(1000)
    await page.locator("label", has_text="City, state, or zip code").press("Enter")

    return page

async def apply_filers(page, dict_user_opts):
    """Function to apply linkedin search filters

    Parameters
    ----------
        page : playwright object
            playwright page object

    Returns
    -------
        page : playwright object
            playwright page object
        dict_user_opt_search_save_apply : dict
            Dictionary with the user options of search, save and apply  
    """
    # Easy Apply filter
    if dict_user_opts["easy_apply_filter"]:
        await page.wait_for_timeout(500)
        await page.get_by_label("Easy Apply filter.").click()
        await page.wait_for_timeout(750)
    
    # Date posted filter
    date_posted_filter = dict_user_opts["date_posted_filter"]
    if date_posted_filter in ['Any time', 'Past month', 'Past week', 'Past 24 hours']:
        await page.wait_for_timeout(1000)
        await page.locator("button", has_text="Date Posted").click()
        await page.wait_for_timeout(1000)
        await page.get_by_text(date_posted_filter, exact=True).click()
        await page.locator("button", has_text="Date Posted").click()
    
    # Experience level filter
    experience_level_filters = dict_user_opts["experience_level_filter"]
    if set(experience_level_filters).issubset(['Internship', 'Entry level', 'Associate', 'Mid-Senior level', 'Director', 'Executive']):
        await page.wait_for_timeout(1000)
        await page.locator("button", has_text="Experience Level").click()
        await page.wait_for_timeout(1000)
        for experience_level_filter in experience_level_filters:
            await page.get_by_text(experience_level_filter, exact=True).click()
            await page.wait_for_timeout(1000)
        await page.wait_for_timeout(1000)
        await page.locator("button", has_text="Experience Level").click()

    # How to work filter 
    how_to_work_filters = dict_user_opts["how_to_work_filter"]
    if set(how_to_work_filters).issubset(['On-site', 'Hybrid', 'Remote']):
        await page.wait_for_timeout(1000)
        await page.locator("button", has_text="On-site/remote").click()
        await page.wait_for_timeout(1000)
        for how_to_work_filter in how_to_work_filters:
            await page.locator("span.t-14", has_text=how_to_work_filter).click()
            await page.wait_for_timeout(1000)
        await page.wait_for_timeout(1000)
        await page.locator("button", has_text="On-site/remote").click()
    
    return page

async def search_job_offers(page, user_search_position, user_search_country, \
    country_search_count, dict_user_opts):
    """Function to search for the job offers in Linkedin

    Parameters
    ----------
        page : playwright object
            playwright page object
        user_search_position : str
            Position to search for
        user_search_country : str
            Country to search for
        country_search_count : int
            Counter to check if is the first search or not
        dict_user_opts : dict
            Dictionary with the user options of search, save and apply  

    Returns
    -------
        page : playwright object
            playwright page object
    """
    # If is the first search, search for the job position and country, else just the country
    if country_search_count == 1:
        # Search for the job position and country
        page = await search_job_position(page, user_search_position)
        page = await search_job_country(page, user_search_country)
        page = await apply_filers(page, dict_user_opts)

        return page
    else:
        # Search for the country
        page = await search_job_country(page, user_search_country)
    
        return page

async def scrap_apply_jobs_page(page, user_search_position, user_search_country, dict_user_opts, nlp):
    """Function that performs the scrap decide if apply and apply actions to a job search results page
    Parameters
    ----------
        page : playwright object
            playwright page
        user_search_position : str
            Position to search for
        user_search_country : str
            Country to search for
        dict_user_opts : dict
            Dictionary with the user options of search, save and apply
        nlp : spacy nlp model
            Spacy nlp model to be used
    Returns
    -------
        list_jobs_instances : list
            List of job instances with the jobs information
    """
    
    list_jobs_instances = [] # List of job instances to save to the json (After scrapping one website page)
    
    logger = logging.getLogger('scrap_apply_jobs_page')

    await page.wait_for_timeout(3000)

    # Locate the list of jobs results
    for job in await page.locator("ul.scaffold-layout__list-container > li.ember-view").all():
        # Click on each job        
        await job.click()

        await page.wait_for_timeout(2000)
        
        # Get the html code of the job
        job_html = await page.content()
        
        # Scrap the job information
        try:
            job_inst = scrap_job(job_html) # Get the job instance with the scrapped info
        except:
            logger.warn("Skipping job due to problem while scraping the information")
            continue

        # Add to the job instance the search_position and search_country
        job_inst.search_position = user_search_position
        job_inst.search_country = user_search_country

        logger.info(f"Check if apply: {job_inst.position_name}, {job_inst.company}, {job_inst.url}")
        # Check the description to decide if apply or not. Also get the email if must be applied sending email
        # instead of EasyApply, and Reasons not to apply and job tags 
        job_inst.apply, job_inst.email, job_inst.reason_not_apply, \
        job_inst.list_tech_no_knowledge, job_inst.list_tags,  \
        job_inst.description = check_apply_or_not(job_inst.description, job_inst.position_name, nlp)

        # Check if there is an Easy Apply Button
        bool_easy_apply_button = await check_easy_apply_button(page)
        logger.info(f"EasyApply button: {bool_easy_apply_button}")
        if not bool_easy_apply_button and job_inst.apply:
            job_inst.manual_apply = True

        # If it was decided to apply and there is not an email in the description (many require to send an email)
        if job_inst.apply and not job_inst.email and dict_user_opts["apply_with_easy_apply"] and bool_easy_apply_button:
            logger.info(f"Apply: {job_inst.position_name}, {job_inst.company}, {job_inst.url}")
            job_inst = await easy_apply(page, job_inst, dict_user_opts)
            logger.info(f"Applied: {job_inst.applied}")

        # Scroll with the mouse
        try:
            await page.mouse.move(x=100, y=300)
            await page.mouse.wheel(delta_x=0.0, delta_y=140.0)
        except:
            continue

        # Append the job instance to a list
        list_jobs_instances.append(job_inst)

    return list_jobs_instances