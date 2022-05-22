"""Implementation of filter-surrounded-by-spaces rule."""

import sys
from typing import TYPE_CHECKING, Any, Dict, List, Union

from ansiblelint.rules import AnsibleLintRule

if TYPE_CHECKING:
    from typing import Optional

    from ansiblelint.file_utils import Lintable


def string_violates_rule(text: str) -> bool:
    """Checks if every | character in the provided string is surrounded by whitespaces"""

    if len(text) < 2:
        return False

    for idx, chr in enumerate(text):
        if chr != "|":
            continue

        # don't check the character before first character or character after last character
        # else, check previous and next next character to see if they are white spaces
        if idx == 0 and not text[idx + 1].isspace():
            return True
        elif idx == len(text) - 1 and not text[idx - 1].isspace():
            return True
        elif not text[idx - 1].isspace() or not text[idx + 1].isspace():
            return True
    return False


def container_violates_rule(container: str | List[Any] | Dict[Any, Any]) -> bool:
    """Recursively check the provided container variable to see if the control is violated"""

    if isinstance(container, str):
        return string_violates_rule(container)
    elif isinstance(container, list):
        return any(True for elem in container if container_violates_rule(elem))
    elif isinstance(container, dict):
        return any(
            True for _, value in container.items() if container_violates_rule(value)
        )
    return False


class FilterSurroundedBySpacesRule(AnsibleLintRule):
    """All filters or pipe characters should have spaces around them."""

    id = "filter-surrounded-by-spaces"
    description = """
All filters should have be surrounded by spaces for readability like following:
```
- ansible_facts.network_resources.bfd_interfaces | symmetric_difference(result.after) | length
```

The following will trigger the rule because spaces do not surround `|`.
```
- ansible_facts.network_resources.bfd_interfaces|symmetric_difference(result.after)|length
```
    """
    severity = "MEDIUM"
    tags = ["experimental", "idiom"]
    version_added = "v6.2.1"

    def matchtask(
        self, task: Dict[str, Any], file: "Optional[Lintable]" = None
    ) -> Union[bool, str]:
        return container_violates_rule(task)


# testing code to be loaded only with pytest or when executed the rule file
if "pytest" in sys.modules:

    import pytest

    from ansiblelint.testing import RunFromText  # pylint: disable=ungrouped-imports

    GOOD_EXAMPLE_LOOP = """
- hosts: all
  tasks:
    - name: Register a file content as a variable
      ansible.builtin.shell: cat /some/path/to/multidoc-file.yaml
      register: result

    - name: Print the transformed variable
      ansible.builtin.debug:
        msg: '{{ item | list }}'
      loop: '{{ result.stdout | from_yaml_all | list }}'
"""

    BAD_EXAMPLE_LOOP = """
- hosts: all
  tasks:
    - name: Register a file content as a variable
      ansible.builtin.shell: cat /some/path/to/multidoc-file.yaml
      register: result

    - name: Bad msg
      ansible.builtin.debug:
        msg: '{{ item|list }}'
      loop: '{{ result.stdout | from_yaml_all | list }}'

    - name: Bad loop 1
      ansible.builtin.debug:
        msg: '{{ item }}'
      loop: '{{ result.stdout|from_yaml_all|list }}'

    - name: Bad loop 2
      ansible.builtin.debug:
        msg: '{{ item }}'
      loop: '{{ result.stdout| from_yaml_all |list }}'

    - name: Bad loop 3
      ansible.builtin.debug:
        msg: '{{ item }}'
      loop: '{{ result.stdout |from_yaml_all| list }}'
"""

    GOOD_EXAMPLE_COMMAND = """
- hosts: all
  tasks:
    - name: handle command output with return code
      ansible.builtin.command: cat {{ my_file | quote }}
      register: my_output
      changed_when: my_output.rc != 0
"""

    BAD_EXAMPLE_COMMAND = """
- hosts: all
  tasks:
    - name: handle command output with return code
      ansible.builtin.command: cat {{ my_file|quote }}
      register: my_output
      changed_when: my_output.rc != 0
"""

    @pytest.mark.parametrize(
        "rule_runner", (FilterSurroundedBySpacesRule,), indirect=["rule_runner"]
    )
    def test_filter_spacing_loop_pass(rule_runner: RunFromText) -> None:
        """This should pass since spaces surround | in both msg and loop"""
        results = rule_runner.run_playbook(GOOD_EXAMPLE_COMMAND)
        assert len(results) == 0

    @pytest.mark.parametrize(
        "rule_runner", (FilterSurroundedBySpacesRule,), indirect=["rule_runner"]
    )
    def test_filter_spacing_loop_fail(rule_runner: RunFromText) -> None:
        """This should fail with 4 failures since spaces do not surround | in both msg and loop in any of the tasks"""
        results = rule_runner.run_playbook(BAD_EXAMPLE_LOOP)
        assert len(results) == 4
        for result in results:
            assert result.message == FilterSurroundedBySpacesRule().shortdesc

    @pytest.mark.parametrize(
        "rule_runner", (FilterSurroundedBySpacesRule,), indirect=["rule_runner"]
    )
    def test_filter_spacing_command_pass(rule_runner: RunFromText) -> None:
        """This should pass since spaces surround | in ansible.builtin.command"""
        results = rule_runner.run_playbook(GOOD_EXAMPLE_LOOP)
        assert len(results) == 0

    @pytest.mark.parametrize(
        "rule_runner", (FilterSurroundedBySpacesRule,), indirect=["rule_runner"]
    )
    def test_filter_spacing_command_fail(rule_runner: RunFromText) -> None:
        """This should fail since spaces do not surround | in ansible.builtin.command"""
        results = rule_runner.run_playbook(BAD_EXAMPLE_COMMAND)
        assert len(results) == 1
        for result in results:
            assert result.message == FilterSurroundedBySpacesRule().shortdesc
