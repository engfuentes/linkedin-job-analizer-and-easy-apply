import asyncio, logging
from playwright.async_api import async_playwright
from modules.helper_functions import load_user_search_save_apply_options, logger_config, \
    get_total_number_job_pages, save_jobs_information, log_exceptions
from modules.main_page_functions import create_broswer_page, search_job_offers,\
    scrap_apply_jobs_page, search_job_offers

# Configure logger
logger_config()

logger = logging.getLogger('main')

logger.info(f"Starting main...")

# Load the user options
dict_user_opts = load_user_search_save_apply_options()

async def run(p):
    """Main function"""
    # Create Broswer and apply filters
    page, browser, context = await create_broswer_page(p)

    # Get positions and countries
    positions = dict_user_opts['search_positions']
    countries = dict_user_opts['search_countries']

    for user_search_position in positions:
        country_search_count = 0
        for user_search_country in countries:
            country_search_count +=1

            logger.info(f"User Search Position: {user_search_position}")
            logger.info(f"User Search Country: {user_search_country}")

            # Perform the job_search
            page = await search_job_offers(page, user_search_position, user_search_country, \
                country_search_count, dict_user_opts)

            # Get the total number of job pages
            page_number, max_number_pages = await get_total_number_job_pages(page)
            
            await page.wait_for_timeout(1000)

            logger.info(f"Num pages {user_search_country}: {max_number_pages}")

            while page_number < max_number_pages + 1:
                try:
                    logger.info(f"Starting page: {page_number}")
                    page_number += 1
                    
                    # Scrap, decide if apply and apply
                    list_jobs_instances = await scrap_apply_jobs_page(page, user_search_position, user_search_country,\
                                            dict_user_opts)

                    save_jobs_information(list_jobs_instances, dict_user_opts)

                    # check again the total number of job pages (thanks to scrolling it can detect it)
                    _, max_number_pages = await get_total_number_job_pages(page) 
                    logger.info(f"Num pages {user_search_country}: {max_number_pages}")

                    # Click the next page
                    if await page.locator(f"button[aria-label='Page {page_number}']").count() != 0:
                        await page.locator(f"button[aria-label='Page {page_number}']").click()

                    logger.info(f"Finished page: {page_number-1}")

                except Exception as e:
                    log_exceptions(e, logger)
                    break

    logger.info(f"Closing broswer...")
    await context.close()
    await browser.close()

async def main():
    async with async_playwright() as p:
        await run(p)

asyncio.run(main())