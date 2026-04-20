from opensprite.context.file_builder import FileContextBuilder
from opensprite.context.paths import sync_templates
from opensprite.documents.user_profile import create_user_profile_store


def test_file_builder_loads_the_user_profile_for_the_active_session(tmp_path):
    app_home = tmp_path / "home"
    sync_templates(app_home, silent=True)

    builder = FileContextBuilder(
        app_home=app_home,
        bootstrap_dir=app_home / "bootstrap",
        memory_dir=app_home / "memory",
        tool_workspace=app_home / "workspace",
        default_skills_dir=tmp_path / "skills",
    )

    profile_a = create_user_profile_store(app_home, "telegram:user-a")
    profile_b = create_user_profile_store(app_home, "telegram:user-b")
    profile_a.write_managed_block("- Prefers dark mode.")
    profile_b.write_managed_block("- Prefers light mode.")

    prompt_a = builder.build_system_prompt("telegram:user-a")
    prompt_b = builder.build_system_prompt("telegram:user-b")

    assert "- Prefers dark mode." in prompt_a
    assert "- Prefers dark mode." not in prompt_b
    assert "- Prefers light mode." in prompt_b
    assert "- Prefers light mode." not in prompt_a
    assert str(profile_a.user_profile_file.resolve()) in prompt_a
    assert str(profile_b.user_profile_file.resolve()) in prompt_b
