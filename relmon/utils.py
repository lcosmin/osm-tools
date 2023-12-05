import logging
from typing import TYPE_CHECKING, List, Any
import sys
import json
import io
from pydantic import BaseModel
from difflib import context_diff, unified_diff

import yaml
import osmapi

from .models import Relation, Diff


log = logging.getLogger()



def flatten_dict(d: Any, prefix: str) -> List[str]:
    """Returns a nested dictionary as a list of dotted keys and values, suitable for comparison.

    For example,

    {"a": {"b": 1}, "c": 2} -->

    a.b=1
    c=2
    """

    keys: List[str] = []

    if type(d) == dict:
        for k, v in d.items():
            keys.extend(flatten_dict(v, f"{prefix}.{k}"))
    elif type(d) == list:
        for i, v in enumerate(d):
            keys.extend(flatten_dict(v, f"{prefix}.{i:04}"))
    else:
        keys.append(f"{prefix}={d}")

    return sorted(keys)


def get_relation_from_api(api: osmapi.OsmApi, rel_id: str) -> Relation:
    """Retrieves a relation and its components from OSM API"""
    return Relation.model_validate(get_relation_dict(api, rel_id))


def get_relation_ids_from_file(path: str):
    """Returns relation ids from a yaml file"""
    with open(path) as f:
        data = yaml.safe_load(f)
        yield from data["relations"]


def get_relation_from_file(path: str) -> Relation:
    """Loads a relation and its members from a local file"""
    with open(path) as f:
        return Relation.model_validate_json(f.read())


def relation_as_list(r: "Relation") -> List[str]:
    return flatten_dict(r.model_dump(), "rel")


def compare_relations(new: Relation, old: Relation) -> List[str]:
    """Compares two relations by dumping them to a text format and performing unified diff on it.
    
    Returns the unified diff as a list of strings.
    """
    rel_id = old.id

    if new == old:
        return []  

    return list(
        unified_diff(
            relation_as_list(old),
            relation_as_list(new),
            fromfile=f"{rel_id}.old",
            tofile=f"{rel_id}.new",
            n=0,
        )
    )


def get_relation_dict(api: "osmapi.OsmApi", rel_id: str) -> dict:
    relation = api.RelationGet(rel_id)

    # do a deep dive in the relation's members and fetch extra info for them
    # to see if changes occured there

    expanded = {}

    for k, v in relation.items():
        if k != "member":
            expanded[k] = v
            continue

        members = []
        for m in v:
            if m["type"] == "node":
                log.debug(f"getting node {m['ref']} data")
                data = api.NodeGet(m["ref"])
            elif m["type"] == "way":
                log.debug(f"getting way {m['ref']} data")
                data = api.WayGet(m["ref"])
            else:
                log.error(f"unhandled type {m['type']}")
                data = None

            members.append(
                {
                    "type": m["type"],
                    "role": m["role"],
                    "data": data,
                }
            )

        expanded["members"] = members

    return expanded


def generate_report(rel_id: int, new: Relation, old: Relation, changes: List[Diff]) -> str:

    diff = io.StringIO()


    log.info(f"------------------------------------")
    print(f"relation {rel_id} changed:\n\n", file=diff)

    for change in changes:
        path = change.get_path()

        # based on the path, determine what the current change
        # is about: the relation itself, its tags or its members
        if path.startswith("members."):
            parts = path.split(".")
            member_pos = int(parts[1])-1

            # len(parts) == 2 (e.g. parts = "members.192") means an added / removed member
            # more than 2 means a change in a member

            what = ""
            if len(parts) > 2:
                if parts[2] == "type":
                    what = "type"
                elif parts[2] == "role":
                    what = "role"
                else:
                    what = "data"

            if change.new is None:
                print(f"member #{member_pos} ({old.members[member_pos].type}) removed, was: {change.old_str}", file=diff)
            elif change.old is None:
                print(f"member #{member_pos} ({new.members[member_pos].type}) added: {change.new_str}", file=diff)
            else:
                if what:
                    additional = f"'s {what}"
                else:
                    additional = ""
                print(f"member #{member_pos} ({new.members[member_pos].type}){additional} changed: {change.old_str} -> {change.new_str}", file=diff)

        elif path.startswith("tag."):
            if change.new is None:
                print(f"tag {change.key} removed, was: {change.old_str}", file=diff)
            elif change.old is None:
                print(f"tag {change.key} added: {change.new_str})", file=diff)
            else:
                print(f"tag {change.key} changed: {change.old_str} -> {change.new_str}", file=diff)
        else:
            if change.new is None:
                print(f"relation attribute '{path}' removed, was: {change.old_str}", file=diff)
            elif change.old is None:
                print(f"relation attribute '{path}' added: {change.new_str}", file=diff)
            else:
                print(f"relation attribute '{path}' changed: {change.old_str} -> {change.new}", file=diff)            

    res = diff.getvalue()
    diff.close()
    return res
