import os
from e2b_desktop import Sandbox, CommandExitException
from dotenv import load_dotenv
from dataclasses import dataclass
load_dotenv()


from counter_strike.install_cs import install_cs_1_6, connect_to_server, choose_team
from counter_strike.agent import run_agent, AgentSettings

from llms.models import AimingModel, OpenRouterGameplayModel
from llms.tools import MoveTool


E2B_API_KEY = os.environ.get("E2B_API_KEY")
CS_SERVER_IP = os.environ.get("CS_SERVER_IP")

desktop = Sandbox(
    display=":0",  
    resolution=(1920, 1080),  # keep this resolution
    timeout = 3600) 
desktop.stream.start()

# Get stream URL
url = desktop.stream.get_url()
print(url)
url_view = desktop.stream.get_url(view_only=True) # only viewing 
print(url_view)
        
agent_setting = AgentSettings(
    side = "CT",
    open_router_api_key_name="OPENROUTER_API_KEY"
)

aiming_model = AimingModel(model="qwen/qwen2.5-vl-72b-instruct",
                           system_message=agent_setting.aiming_system_prompt,
                           api_key_name=agent_setting.open_router_key_name)

move_tool = MoveTool(desktop=desktop)
tools = {move_tool.name: move_tool}

gameplay_model = OpenRouterGameplayModel(tools=tools, 
                                         model="google/gemini-2.5-flash-preview",
                                         api_key_name=agent_setting.open_router_key_name)


if __name__=="__main__":
    install_cs_1_6(desktop=desktop)
    connect_to_server(desktop=desktop, ip_address=CS_SERVER_IP)
    choose_team(desktop=desktop,
                team_option=agent_setting.team_choice,
                skin=agent_setting.skin_choice)
    
    run_agent(aiming_model=aiming_model,
              gameplay_model=gameplay_model,
              desktop=desktop,
              iterations=20) # For demonstration 
