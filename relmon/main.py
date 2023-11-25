import osmapi 
import argparse
import logging 
import pathlib
import io

from .utils import get_relation_from_api, get_relation_from_file, get_relation_ids_from_file
from .utils import compare_relations, analyze_diff
from .models import diff_relation


logging.getLogger("urllib3").setLevel(logging.ERROR)
logging.getLogger("osmapi").setLevel(logging.ERROR)

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s]: %(message)s")
log = logging.getLogger()



def main():

    p = argparse.ArgumentParser(prog="osm-rel-mon", 
                                description="This tool monitors OSM relations (public transport in particular) for changes")

    p.add_argument("-s", "--save", metavar="rel-ID", help="save single relation to file")
    p.add_argument("-c", "--compare", metavar="rel-ID", help="compare relation to previously saved data")
    p.add_argument("-S", "--save-from-file", help="save relations identified by IDs loaded from file")
    p.add_argument("-m", "--monitor-from-file", help="Monitor relations identified by IDs loaded from file")
    p.add_argument("-d", "--data", help="directory for saving data", default=".data", type=pathlib.Path)

    args = p.parse_args()

    api = osmapi.OsmApi()

    if args.save:
        log.debug(f"getting relation id {args.save}")

        new = get_relation_from_api(api, args.save)

        with open(f"{args.data/args.save}.json", "w") as f:
            f.write(new.model_dump_json())

    if args.compare:
        old = get_relation_from_file(f"{args.data/args.compare}.json")     
        new = get_relation_from_api(api, args.compare)

        if old != new: 
            diff = compare_relations(new, old)
            if diff:
                log.info("\n".join(diff))
        

    if args.save_from_file:
        for rel_id in get_relation_ids_from_file(args.save_from_file):
            log.info(f"saving relation {rel_id}...")

            new = get_relation_from_api(api, rel_id)

            with open(f"{args.data/rel_id}.json", "w") as f:
                f.write(new.model_dump_json())
        

    if args.monitor_from_file:

        for rel_id in get_relation_ids_from_file(args.monitor_from_file):
            log.info(f"analyzing relation {rel_id}...")
            try:
                old = get_relation_from_file(f"{args.data/rel_id}.json")
            except Exception as e:
                log.error(f"[{rel_id}] error loading existing relation data: {e}")
                continue

            try:
                new = get_relation_from_api(api, rel_id)
            except Exception as e:
                log.error(f"[{rel_id}] error loading OSM relation data")
                continue

            changes = diff_relation(new, old)
            if changes:

                diff = analyze_diff(new.id, changes)
                log.info(diff)
               
