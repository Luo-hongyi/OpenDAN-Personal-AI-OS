from typing import Any
from pathlib import Path
import os
import logging
import toml
import aiofiles

# fetching model price
import litellm

logger = logging.getLogger(__name__)

_file_dir = os.path.dirname(__file__)

class ResourceLocation:
    def __init__(self) -> None:
        pass

class FeatureItem:
    def __init__(self) -> None:
        pass

class UserConfigItem:
    def __init__(self,desc:str=None) -> None:
        self.default_value = None 
        self.is_optional = False
        self.item_type = "str"
        self.desc = desc
        self.value = None
        self.user_set = False

    def clone(self):
        new_config_item = UserConfigItem()
        new_config_item.default_value = self.default_value
        new_config_item.is_optional = self.is_optional
        new_config_item.desc = self.desc
        new_config_item.item_type = self.item_type
        new_config_item.value = self.value
        return new_config_item

class UserConfig:
    def __init__(self) -> None:
        self.config_table = {}
        self.user_config_path:str = None

        self._init_default_value("llm_default_model","gpt-4o")
        self._init_default_value("llm_plan_models",["gpt-4o"])
        self._init_default_value("llm_outline_models",["gpt-3.5-turbo"])
        self._init_default_value("llm_swift_models",["gpt-3.5-turbo"])

        # add two abstract model types
        self._init_default_value("llm_reason_models",["o3"])
        self._init_default_value("llm_code_models",["gpt-4.1"])



    def _init_default_value(self,key:str,value:Any) -> None:
        if self.config_table.get(key) is not None:
            logger.warning("user config key %s already exist, will be overrided",key)
        
        new_config_item = UserConfigItem()
        new_config_item.default_value = value
        new_config_item.is_optional = True
        self.config_table[key] = new_config_item

    
    def sort_llm_models_by_cost(self,key:str):
        if key not in ["llm_plan_models", "llm_outline_models", "llm_swift_models", "llm_reason_models", "llm_code_models"]:
            logger.warning("Invalid key for sorting LLM models: %s", key)
            return
        models = self.get_value(key)
        if models is None or not isinstance(models, list):
            logger.warning("No valid models found for key: %s", key)
            return
        if len(models) == 1:
            return
        try:
            # keep the first model as it is the default highest performance model
            sorted_models = [models[0]]
            # Fetch the cost for each model
            models_with_cost = []
            for model in models:
                try:
                    cost = litellm.model_cost.get(model)["input_cost_per_token"]
                    models_with_cost.append((model, cost))
                except Exception as e:
                    logger.error(f"Failed to get cost for model {model}: {str(e)}")
                    continue
            # Sort models by cost
            models_with_cost.sort(key=lambda x: x[1])
            # Update the config with sorted models
            sorted_models.extend([model for model, cost in models_with_cost])
            self.set_value(key, sorted_models)
            logger.info(f"Models for {key} sorted by cost: {sorted_models}")
        except Exception as e:
            logger.error(f"Error sorting models for {key}: {str(e)}")
            return
        

    def llm_get_real_model_name(self,mode_name:str,mode="performance_first") -> str:
        choice_index = 0
        if mode == "performance_first":
            choice_index = 0
        elif mode == "cost_first":
            choice_index = -1
            
        default_model_name = self.get_value("llm_default_model")[choice_index]
        plan_llm_model_name = self.get_value("llm_plan_models")[choice_index]
        outline_model_name = self.get_value("llm_outline_models")[choice_index]
        swift_model_name = self.get_value("llm_swift_models")[choice_index]

        # add two abstract model types
        reason_model_name = self.get_value("llm_reason_models")[choice_index]
        code_model_name = self.get_value("llm_code_models")[choice_index]

        if mode_name is None:
            return default_model_name
        if mode_name == "default":
            return default_model_name
        if mode_name == "plan_llm":
            return plan_llm_model_name
        if mode_name == "outline_llm":
            return outline_model_name
        if mode_name == "swift_llm":
            return swift_model_name

        # add two abstract model types
        if mode_name == "reason_llm":
            return reason_model_name
        if mode_name == "code_llm":
            return code_model_name
        
        return mode_name
    
    def add_user_config(self,key:str,desc:str,is_optional:bool,default_value:Any=None,item_type="str") -> None:
        if self.config_table.get(key) is not None:
            logger.warning("user config key %s already exist, will be overrided",key)
    
        new_config_item = UserConfigItem()
        new_config_item.default_value = default_value
        new_config_item.is_optional = is_optional
        new_config_item.desc = desc
        new_config_item.item_type = item_type
        self.config_table[key] = new_config_item
        
    async def load_value_from_file(self,file_path:str,is_user_config = False) -> None:
        try: 
            all_config = toml.load(file_path)
            if all_config is not None:
                for key,value in all_config.items():
                    config_item = self.config_table.get(key)
                    if config_item is None:
                        logger.warning("user config key %s not exist",key)
                        continue
                    config_item.value = value
                    config_item.user_set = is_user_config

        except Exception as e:
            logger.warn(f"load user config from {file_path} failed!")


    async def save_to_user_config(self) -> None:
        will_save_config = {}
        for key,value in self.config_table.items():
            if value.user_set:
                will_save_config[key] = value.value
        
        if len(will_save_config) > 0:
            try:
                directory = os.path.dirname(self.user_config_path)
                if not os.path.exists(directory):
                    os.makedirs(directory)

                async with aiofiles.open(self.user_config_path,"w") as f:
                    toml_str = toml.dumps(will_save_config)
                    await f.write(toml_str)
            except Exception as e:
                logger.error(f"save user config to {self.user_config_path} failed!")
                return False
        
        return True

    def get_config_item(self,key:str) -> Any:
        config_item = self.config_table.get(key)
        if config_item is None:
            logger.warning(f"user config key {key} not exist")
            return None

        return config_item
    
    def get_value(self,key:str)->Any:
        config_item = self.config_table.get(key)
        if config_item is None:
            logger.warning(f"user config key {key} not exist")
            return None
        
        if config_item.value is None:
            return config_item.default_value

        return config_item.value

    def set_value(self,key:str,value:Any) -> None:
        config_item = self.config_table.get(key)
        if config_item is None:
            logger.warning("user config key %s not exist",key)
            return 
        
        config_item.value = value
        config_item.user_set = True
        #TODO: save to file?

        
    def check_config(self) -> None:
        check_result = {}
        for key,config_item in self.config_table.items():
            if config_item.value is None and not config_item.is_optional:
                check_result[key] = config_item
        
        if len(check_result) > 0:
            return check_result
        else:
            return None

# storage sytem for current user
class AIStorage:
    _instance = None
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = AIStorage()
        return cls._instance

    def __init__(self) -> None:
        self.is_dev_mode = False
        self.user_config = UserConfig()
        self.feature_init_results = {}

    async def initial(self)->bool:
        self.user_config.user_config_path = str(self.get_myai_dir() + "/etc/system.cfg.toml")
        await self.user_config.load_value_from_file(self.get_system_dir() + "/system.cfg.toml")
        await self.user_config.load_value_from_file(self.user_config.user_config_path,True)

    async def enable_feature(self,feature_name:str) -> None:
        self.user_config.set_value(f"feature.{feature_name}","True")
        await self.user_config.save_to_user_config()
        

    async def disable_feature(self,feature_name:str) -> None:
        self.user_config.set_value(f"feature.{feature_name}","False")
        await self.user_config.save_to_user_config()
    
    async def set_feature_init_result(self,feature_name:str,result:bool) -> None:
        self.feature_init_results[feature_name] = result

    async def is_feature_enable(self,feature_name:str) -> bool:
        is_enable = self.user_config.get_value(f"feature.{feature_name}")
        if is_enable is None:
            return False
        
        init_result = self.feature_init_results.get(feature_name)
        if init_result:
            if init_result is False:
                return False
        
        if is_enable == "True":
            return True
        return False

    def get_user_config(self) -> UserConfig:
        return self.user_config

    def get_system_dir(self) -> str:
        """ 
        system dir is dir for aios system
        /opt/aios
        """
        if self.is_dev_mode:
            return os.path.abspath(_file_dir + "/../../")
        else:
            return "/opt/aios/"
        
    
    def get_system_app_dir(self)->str:
        """
        system app dir is the dir for aios build-in app 
        /opt/aios/app
        """
        if self.is_dev_mode:
            return os.path.abspath(_file_dir + "/../../../rootfs/")
        else:
            return "/opt/aios/app/"
    
    def get_myai_dir(self) -> str:
        """
        my ai dir is the dir for user to store their ai app and data
        ~/myai/
        """
        return f"{Path.home()}/myai"
    
    def get_download_dir(self) -> str:
        """
        download dir is the dir for user to store the files downloaded with the system.
        ~/myai/download
        """
        return f"{self.get_myai_dir()}/download"
        
    def get_db(self,app_name:str)->ResourceLocation:
        pass

    def open_file(self,file_path:str,options:dict):
        pass

    def get_named_object(self,name:str) -> Any:
        pass

    def put_named_object(self,name:str,obj:Any) -> None:
        pass
    
    async def try_create_file_with_default_value(self,path:str,default_value:str):
        if os.path.exists(path):
            return None
        
        try:
            directory = os.path.dirname(path)
            if not os.path.exists(directory):
                os.makedirs(directory)
            async with aiofiles.open(path,"w") as f:
                await f.write(default_value)

        except Exception as e:
            logger.error(f"open or create file {path} failed! {str(e)}")

    @staticmethod
    def ensure_directory_exists(directory_path):
        if not os.path.exists(directory_path):
            os.makedirs(directory_path)
            logger.info(f"Directory created: {directory_path}")

