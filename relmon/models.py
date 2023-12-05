import datetime
from itertools import zip_longest
from typing import List, Any, Optional
from pydantic import BaseModel, Field


class MemberMixin:
    def name(self) -> str:
        return self.tag.get("name", "")

    def short_str(self) -> str:
        name = self.name()
        return f"[id:{self.id}]" + ("" if not name else f" {name}")


class Diff(BaseModel):
    path: str
    key: str
    old: Any = None
    old_str: str = ""
    new: Any = None
    new_str: str = ""

    def get_path(self) -> str:
        if self.path:
            return f"{self.path}.{self.key}"
        return self.key


class Node(BaseModel, MemberMixin):
    id: int
    visible: bool
    version: int
    changeset: int
    timestamp: datetime.datetime
    user: str
    uid: int
    lat: float
    lon: float
    tag: dict = Field(default={})


class Way(BaseModel, MemberMixin):
    id: int
    visible: bool
    version: int
    changeset: int
    timestamp: datetime.datetime
    user: str
    uid: int
    tag: dict = Field(default={})
    nd: List[int]


class Member(BaseModel):
    type: str
    role: str
    data: Node | Way


class Relation(BaseModel):
    id: int
    visible: bool
    version: int
    timestamp: datetime.datetime
    changeset: int
    user: str
    uid: int
    tag: dict
    members: List[Member]


def diff_relation(new: Relation, old: Relation) -> List[Diff]:
    diffs: List[Diff] = []

    members = False
    tags = False

    # iterate the relation models by fields and compare them to find
    # changes. 'tags' and 'members' are handled differently and are
    # checked at the end, so that the "top level" relation changes
    # are returned first
    for field in new.model_fields_set:
        if field == "members":
            members = True
        elif field == "tag":
            tags = True
        else:
            o = getattr(old, field)
            n = getattr(new, field)

            if o != n:
                diffs.append(
                    Diff(
                        path="",
                        key=field,
                        new=n,
                        new_str=str(n),
                        old=o,
                        old_str=str(o),
                    )
                )

    if tags:
        o_keys = old.tag.keys()
        n_keys = new.tag.keys()

        # extra keys in the new tags ?
        for k in n_keys - o_keys:
            diffs.append(
                Diff(
                    path="",
                    key=f"tag.{k}",
                    new=new.tag[k],
                    new_str=str(new.tag[k])
                )
            )

        for k in o_keys - n_keys:
            diffs.append(
                Diff(
                    path="",
                    key=f"tag.{k}",
                    old=old.tag[k],
                    old_str=str(old.tag[k])
                )
            )

        for k in o_keys & n_keys:
            if old.tag[k] != new.tag[k]:
                diffs.append(
                    Diff(
                        path="",
                        key=f"tag.{k}",
                        new=new.tag[k],
                        new_str=str(new.tag[k]),
                        old=old.tag[k],
                        old_str=str(old.tag[k])
                    )
                )

    if members:
        pos = -1
        for n, o in zip_longest(new.members, old.members, fillvalue=None):
            pos += 1
            if n is None:
                diffs.append(
                    Diff(
                        path=f"members",
                        key=str(pos),
                        old=o,
                        old_str=o.data.short_str(),
                        old_item=o,
                    )
                )
            elif o is None:
                diffs.append(
                    Diff(
                        path=f"members",
                        key=str(pos),
                        new=n,
                        new_str=n.data.short_str(),
                        new_item=n,
                    )
                )
            else:
                # compare the members: type, role, id
                if n.type != o.type:
                    diffs.append(
                        Diff(
                            path=f"members.{pos}",
                            key="type",
                            old=o.type,
                            old_str=o.type,
                            new=n.type,
                            new_str=n.type,
                            old_item=o,
                            new_item=n,
                        )
                    )

                if n.role != o.role:
                    diffs.append(
                        Diff(
                            path=f"members.{pos}",
                            key="role",
                            old=o.role,
                            old_str=o.role,
                            new=n.role,
                            new_str=n.role,
                            old_item=o,
                            new_item=n,
                        )
                    )

                if n.data.id != o.data.id:
                    diffs.append(
                        Diff(
                            path=f"members.{pos}.data",
                            key="id",
                            old=o.data.id,
                            old_str=o.data.short_str(),
                            new=n.data.id,
                            new_str=n.data.short_str(),
                            old_item=o,
                            new_item=n,
                        )
                    )

                # TODO: do a deep dive to compare members themselves

    return diffs
