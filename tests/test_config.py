"""Tests for the SSH-config-backed inventory adapter."""

import textwrap

import pytest

from lab_sentinel.adapters.config import SSHConfigInventoryAdapter
from lab_sentinel.domain.errors import HostNotFoundError

SSH_CONFIG = textwrap.dedent(
    """
    Host proxy109
        HostName 200.132.136.134
        User emanuel
        Port 22
        IdentityFile ~/.ssh/id_ed25519_209

    Host raspi01-proxy
        HostName localhost
        User emanuel
        Port 2400
        ProxyJump proxy109

    Host raspi02-proxy
        HostName localhost
        User emanuel
        Port 2401
        ProxyJump proxy109

    Host pc209 proxy209
        HostName 200.132.136.139
        User emanuel
        Port 22
        IdentityFile ~/.ssh/id_ed25519_209
    """
)

GROUPS_YAML = textwrap.dedent(
    """
    groups:
      laboratorio-109:
        - raspi01-proxy
        - raspi02-proxy
        - proxy109
    """
)


@pytest.fixture
def ssh_config_file(tmp_path):
    path = tmp_path / "ssh_config"
    path.write_text(SSH_CONFIG)
    return path


def test_parses_basic_host_entry(ssh_config_file):
    inv = SSHConfigInventoryAdapter(ssh_config_file)
    host = inv.get_host("proxy109")
    assert host.host == "200.132.136.134"
    assert host.user == "emanuel"
    assert host.port == 22
    assert host.identity_file is not None


def test_parses_proxy_jump_host(ssh_config_file):
    inv = SSHConfigInventoryAdapter(ssh_config_file)
    host = inv.get_host("raspi01-proxy")
    assert host.host == "localhost"
    assert host.port == 2400
    assert host.proxy_jump == "proxy109"


def test_multiple_aliases_in_one_block_are_both_registered(ssh_config_file):
    inv = SSHConfigInventoryAdapter(ssh_config_file)
    assert inv.get_host("pc209").host == "200.132.136.139"
    assert inv.get_host("proxy209").host == "200.132.136.139"


def test_unknown_host_raises_error(ssh_config_file):
    inv = SSHConfigInventoryAdapter(ssh_config_file)
    with pytest.raises(HostNotFoundError):
        inv.get_host("does-not-exist")


def test_list_hosts_returns_all(ssh_config_file):
    inv = SSHConfigInventoryAdapter(ssh_config_file)
    names = {h.name for h in inv.list_hosts()}
    assert {"proxy109", "raspi01-proxy", "raspi02-proxy", "pc209", "proxy209"} <= names


def test_loads_sentinel_yaml_groups(ssh_config_file, tmp_path):
    groups_file = tmp_path / ".sentinel.yaml"
    groups_file.write_text(GROUPS_YAML)
    inv = SSHConfigInventoryAdapter(ssh_config_file, groups_file=groups_file)
    hosts = inv.list_hosts(group="laboratorio-109")
    names = {h.name for h in hosts}
    assert names == {"raspi01-proxy", "raspi02-proxy", "proxy109"}


def test_explicit_group_tags_are_attached(ssh_config_file, tmp_path):
    groups_file = tmp_path / ".sentinel.yaml"
    groups_file.write_text(GROUPS_YAML)
    inv = SSHConfigInventoryAdapter(ssh_config_file, groups_file=groups_file)
    assert "laboratorio-109" in inv.get_host("proxy109").tags


def test_auto_groups_by_naming_convention(ssh_config_file):
    # No groups file -> auto-group by the `<device>-<env>` suffix.
    inv = SSHConfigInventoryAdapter(ssh_config_file)
    hosts = inv.list_hosts(group="proxy")
    names = {h.name for h in hosts}
    assert {"raspi01-proxy", "raspi02-proxy"} <= names


def test_works_fully_without_sentinel_yaml(ssh_config_file, tmp_path):
    # Groups are optional: with no .sentinel.yaml the whole inventory is still
    # usable straight from ~/.ssh/config. This is the default, zero-config path.
    inv = SSHConfigInventoryAdapter(
        ssh_config_file, groups_file=tmp_path / "nope.yaml"
    )
    all_hosts = inv.list_hosts()
    assert {h.name for h in all_hosts} >= {"proxy109", "raspi01-proxy", "pc209"}
    # A specific host resolves with full connection details.
    assert inv.get_host("raspi01-proxy").port == 2400


def test_identity_file_not_in_public_view(ssh_config_file):
    inv = SSHConfigInventoryAdapter(ssh_config_file)
    public = inv.get_host("proxy109").public_view()
    assert "identity_file" not in public
    assert "id_ed25519" not in str(public)


def test_name_filter_returns_matching_hosts(ssh_config_file):
    inv = SSHConfigInventoryAdapter(ssh_config_file)
    result = inv.list_hosts(name_filter="raspi")
    names = {h.name for h in result}
    assert "raspi01-proxy" in names
    assert "raspi02-proxy" in names
    assert "proxy109" not in names


def test_name_filter_is_case_insensitive(ssh_config_file):
    inv = SSHConfigInventoryAdapter(ssh_config_file)
    assert inv.list_hosts(name_filter="RASPI") == inv.list_hosts(name_filter="raspi")


def test_name_filter_and_group_combine(ssh_config_file, tmp_path):
    groups_file = tmp_path / ".sentinel.yaml"
    groups_file.write_text(
        "groups:\n  laboratorio-109:\n    - raspi01-proxy\n    - raspi02-proxy\n    - proxy109\n"
    )
    inv = SSHConfigInventoryAdapter(ssh_config_file, groups_file=groups_file)
    result = inv.list_hosts(group="laboratorio-109", name_filter="raspi")
    names = {h.name for h in result}
    assert names == {"raspi01-proxy", "raspi02-proxy"}
