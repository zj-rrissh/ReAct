"""Message dataclass 测试 (20 用例)。"""

import pytest
from agents.message import Message


class TestMessageCreation:
    def test_create_message_with_string_payload(self):
        msg = Message(type="task", sender="A", receiver="B", payload="hello")
        assert msg.type == "task"
        assert msg.sender == "A"
        assert msg.receiver == "B"
        assert msg.payload == "hello"

    def test_create_message_with_dict_payload(self):
        msg = Message(type="task", sender="A", receiver="B", payload={"key": "value"})
        assert msg.payload == {"key": "value"}

    def test_create_message_with_list_payload(self):
        msg = Message(type="task", sender="A", receiver="B", payload=[1, 2, 3])
        assert msg.payload == [1, 2, 3]

    def test_create_message_with_none_payload(self):
        msg = Message(type="task", sender="A", receiver="B", payload=None)
        assert msg.payload is None

    def test_create_message_with_custom_object_payload(self):
        class Obj:
            def __str__(self):
                return "CustomObj"
        obj = Obj()
        msg = Message(type="task", sender="A", receiver="B", payload=obj)
        assert msg.payload is obj

    def test_create_message_non_default_type(self):
        msg = Message(type="control", sender="X", receiver="Y", payload="cmd")
        assert msg.type == "control"

    def test_create_message_all_fields_populated(self):
        msg = Message(type="feedback", sender="planner", receiver="orchestrator", payload={"passed": True})
        assert msg.type == "feedback"
        assert msg.sender == "planner"
        assert msg.receiver == "orchestrator"
        assert msg.payload == {"passed": True}


class TestCreateReply:
    def test_create_reply_swaps_sender_receiver(self):
        msg = Message(type="task", sender="orchestrator", receiver="executor", payload="run")
        reply = msg.create_reply("done")
        assert reply.sender == "executor"
        assert reply.receiver == "orchestrator"

    def test_create_reply_preserves_payload(self):
        payload = {"result": "success", "data": [1, 2]}
        msg = Message(type="task", sender="A", receiver="B", payload="req")
        reply = msg.create_reply(payload)
        assert reply.payload == payload

    def test_create_reply_default_type_is_result(self):
        msg = Message(type="task", sender="A", receiver="B", payload="req")
        reply = msg.create_reply("done")
        assert reply.type == "result"

    def test_create_reply_custom_msg_type(self):
        msg = Message(type="task", sender="A", receiver="B", payload="req")
        reply = msg.create_reply({"ok": False}, msg_type="feedback")
        assert reply.type == "feedback"

    def test_create_reply_returns_new_message_instance(self):
        msg = Message(type="task", sender="A", receiver="B", payload="req")
        reply = msg.create_reply("done")
        assert reply is not msg

    def test_create_reply_original_message_unchanged(self):
        msg = Message(type="task", sender="A", receiver="B", payload="req")
        msg.create_reply("done")
        assert msg.sender == "A"
        assert msg.receiver == "B"
        assert msg.type == "task"


class TestRepr:
    def test_repr_short_payload_under_80_chars(self):
        msg = Message(type="task", sender="A", receiver="B", payload="short")
        r = repr(msg)
        assert "short" in r
        assert "..." not in r

    def test_repr_payload_exactly_80_chars(self):
        payload = "x" * 80
        msg = Message(type="task", sender="A", receiver="B", payload=payload)
        r = repr(msg)
        assert "..." not in r

    def test_repr_payload_over_80_chars_truncated(self):
        payload = "x" * 100
        msg = Message(type="task", sender="A", receiver="B", payload=payload)
        r = repr(msg)
        assert "..." in r

    def test_repr_truncated_shows_77_chars_plus_ellipsis(self):
        payload = "a" * 100
        msg = Message(type="task", sender="A", receiver="B", payload=payload)
        r = repr(msg)
        expected_payload = "a" * 77 + "..."
        assert expected_payload in r

    def test_repr_payload_none(self):
        msg = Message(type="task", sender="A", receiver="B", payload=None)
        r = repr(msg)
        assert "None" in r

    def test_repr_payload_dict(self):
        payload = {"key": "value", "num": 42}
        msg = Message(type="task", sender="A", receiver="B", payload=payload)
        r = repr(msg)
        assert "key" in r

    def test_repr_payload_list(self):
        msg = Message(type="task", sender="A", receiver="B", payload=[1, 2, 3])
        r = repr(msg)
        assert "1, 2, 3" in r or "[1, 2, 3]" in r
