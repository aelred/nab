import show
import database
import files
import renamer
import show_tree
from scheduler import scheduler

shows = show_tree.ShowTree()

renamer.init(shows)


def get_data():
    new_shows = show.get_shows()

    for sh in new_shows:
        if not sh.title in shows:
            shows[sh.title] = sh

    database.get_data(shows)
    show.filter_shows(shows)
    files.find_files(shows)

    # reschedule to get data every hour
    scheduler.add(60 * 60, get_data)

scheduler.add(0, get_data)
