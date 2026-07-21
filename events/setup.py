import typing
from discord import Interaction, InteractionType
from commands.create_alliance_invite import create_alliance_invite_selected
from commands.giftcode_add import giftcode_add_solve, giftcode_add, giftcode_add_input 
from commands.admin_panel import create_tncd, manage_alliance_whitelist, manage_alliance_whitelist_add, manage_alliance_whitelist_add_selector, manage_alliance_whitelist_remove, manage_alliance_whitelist_remove_selector, set_gcc_selected, set_gcc_show_selector, set_invite_channel, set_invite_channel_opt, set_jrc_selected, set_jrc_show_selector, set_tncc_selected, set_tncc_show_selector, manage_state_whitelist, manage_state_whitelist_add, manage_state_whitelist_add_selector, manage_state_whitelist_remove, manage_state_whitelist_remove_selector
from commands.create_age_counter import refresh_age_counter
from commands.nickname_manager import set_nickname_on_alliance, set_nickname_on_member
from commands.wos_link_manager import refresh_link_selection, remove_link_selection
from discordHandler import DiscordClient
from services import get_services
from .dashboard import activate_tnc_draft_selector, create_tnc_draft, release_selected_tnc_draft
from .alliance_request import tnc_alliance_join_req, tnc_alliance_join_request_click, tnc_code_join_click, tnc_invite_code_req, link_wos_acc_yes, link_wos_acc_accept, link_wos_acc_reject
from .giftcode_redeem import giftcode_redeem_by_click, giftcode_redeem_click, handle_redeem, handle_redeem_captcha_prompt, handle_redeem_finalize

async def link_wos_acc_no_handler(client: DiscordClient, interaction: Interaction):
    await interaction.response.send_message('Linking of WOS account cancelled', ephemeral=True)

component_events: dict[str, typing.Callable[..., typing.Awaitable]] = {
    'giftcode.redeem': giftcode_redeem_click,
    'giftcode.redeem.by': giftcode_redeem_by_click,
    'button_activate_tnc_draft': activate_tnc_draft_selector,
    'button_create_tnc_draft': create_tnc_draft,
    'release-terms-thread': release_selected_tnc_draft,
    'confirm_tnc_release': release_selected_tnc_draft,
    'gcc.solve': giftcode_add_solve,
    'gcc.refresh': giftcode_add,
    'giftcode.refresh': handle_redeem,
    'giftcode.solve': handle_redeem_captcha_prompt,
    'tnc.alliance_join_req': tnc_alliance_join_request_click,
    'tnc.code_join': tnc_code_join_click,
    'link_wos_acc.yes': link_wos_acc_yes,
    'join_request_accept': link_wos_acc_accept,
    'join_request_reject': link_wos_acc_reject,
    'admin_panel.opt.set_gcc': set_gcc_show_selector,
    'admin_panel.opt.set_tncc': set_tncc_show_selector,
    'admin_panel.opt.create_tncd': create_tncd,
    'admin_panel.opt.set_jrc': set_jrc_show_selector,
    'admin_panel.set_jrc': set_jrc_selected,
    'admin_panel.set_tncc': set_tncc_selected,
    'admin_panel.set_gcc': set_gcc_selected,
    'admin_panel.opt.state_whitelist': manage_state_whitelist,
    'admin_panel.add_state_selector': manage_state_whitelist_add_selector,
    'admin_panel.remove_state_selector': manage_state_whitelist_remove_selector,
    'admin_panel.remove_state': manage_state_whitelist_remove,
    'admin_panel.opt.alliance_whitelist': manage_alliance_whitelist,
    'admin_panel.add_alliance_selector': manage_alliance_whitelist_add_selector,
    'admin_panel.remove_alliance_selector': manage_alliance_whitelist_remove_selector,
    'admin_panel.remove_alliance': manage_alliance_whitelist_remove,
    'admin_panel.opt.set_invite_channel': set_invite_channel_opt,
    'admin_panel.set_invite_channel': set_invite_channel,
    'cai.alliance_select': create_alliance_invite_selected,
    'link_wos_acc.no': link_wos_acc_no_handler,
    'age_counter.refresh': refresh_age_counter,
    'refresh_link.account': refresh_link_selection,
    'remove_link.account': remove_link_selection,
    'nickname.set_on_member': set_nickname_on_member,
    'nickname.set_on_alliance': set_nickname_on_alliance
}

modal_events: dict[str, typing.Callable[..., typing.Awaitable]] = {
    'gcc.input': giftcode_add_input,
    'tnc_alliance_join_req': tnc_alliance_join_req,
    'tnc_invite_code_req': tnc_invite_code_req,
    'admin_panel.add_state': manage_state_whitelist_add,
    'admin_panel.add_alliance': manage_alliance_whitelist_add,
    'giftcode.captcha': handle_redeem_finalize
}

async def handle_event(client: DiscordClient, interaction: Interaction, event_list: dict[str, typing.Callable[..., typing.Awaitable]], event_type: str):
    if not interaction.data:
        await interaction.response.send_message('Invalid interaction (data missing)', ephemeral=True)
        return

    trigger_id = interaction.data.get('custom_id', None)
    if not isinstance(trigger_id, str):
        await interaction.response.send_message('Invalid interaction (event type missing)', ephemeral=True)
        return

    trigger_parts = trigger_id.split('::')
    event_id = trigger_parts[0]
    params = trigger_parts[1:]

    callback = event_list.get(event_id, None)
    if not callback:
        await interaction.response.send_message('Invalid interaction (unhandled event type)', ephemeral=True)
        return

    try:
        await callback(client, interaction, *params)
    except Exception as e:
        print(f'Failed to handle {event_type} {event_id}', str(e))
        try: await interaction.response.send_message('Something went wrong handling your request', ephemeral=True)
        except Exception: pass

async def on_interaction(client: DiscordClient, interaction: Interaction):
    if interaction.type == InteractionType.component and interaction.data:
        await handle_event(client, interaction, component_events, 'component')
        return
    if interaction.type == InteractionType.modal_submit and interaction.data:
        await handle_event(client, interaction, modal_events, 'modal')
        return

async def setup():
    services = get_services()
    await services.discord.on_interaction(on_interaction)
