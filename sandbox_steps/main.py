from abc import ABC, abstractmethod


from e2b_desktop import Sandbox



class DesktopSteps:
    """
    Actions to take to get E2B desktop to a reproducible state. 
    """

    def __init__(self,
                 desktop: "Sandbox"):
        
        self.steps = []


    def run():
        ...


class Step:
    """
    A single action executed in the E2B Sandbox
    """