import asyncio, logging
from playwright.async_api import async_playwright
from modules.helper_functions import load_user_search_save_apply_options, logger_config, \
    get_total_number_job_pages, save_jobs_information, log_exceptions
from modules.main_page_functions import create_broswer_search_apply_filters, \
    scrap_apply_jobs_page

# Configure logger
logger_config()

logger = logging.getLogger('main')

logger.info(f"Starting main...")

# Load the user options
dict_user_opt_search_save_apply = load_user_search_save_apply_options()

logger.info(f"User Search Position: {dict_user_opt_search_save_apply['search_position']}")
logger.info(f"User Search Country: {dict_user_opt_search_save_apply['search_country']}")

async def run(p):
    """Main function"""
    
    # Create Broswer and apply filters
    page, browser = await create_broswer_search_apply_filters(p, dict_user_opt_search_save_apply)

    # Get the total number of job pages
    page_number, max_number_pages = await get_total_number_job_pages(page)
    
    while page_number < max_number_pages:
        try:
            page_number += 1
            
            # Scrap, decide if apply and apply
            list_jobs_instances = await scrap_apply_jobs_page(page, dict_user_opt_search_save_apply)

            save_jobs_information(list_jobs_instances, dict_user_opt_search_save_apply)

            # Click the next page
            await page.locator(f"button[aria-label='Page {page_number}']").click()

            logger.info(f"Finished page: {page_number-1}")

        except Exception as e:
            log_exceptions(e, logger)
            break

    await browser.close()

async def main():
    async with async_playwright() as p:
        await run(p)

asyncio.run(main())