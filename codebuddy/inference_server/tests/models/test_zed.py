# ruff: noqa: F401

import logging
import time

from fastapi import FastAPI
from fastapi.testclient import TestClient

from inference_server.utils.ipython import enable_auto_reload

enable_auto_reload()
from inference_server.codebuddy import get_llm, load_model_by_instance
from inference_server.server.zed_api import setup_zed_apis, extract_input_excerpt, gen_predict_draft

logging.basicConfig(level=logging.DEBUG)


# yapf: disable
async def test_zed(instance, config_path=None):
    await load_model_by_instance(instance, config_path=config_path)
    case1 = {
    "outline": "```copilot_dashboard_analysis/ai_code_ratio.py\ndef get_lang_from_path\ndef get_excluded_patterns\ndef should_ignore_file\ndef format_gerrit_row\ndef extract_email\ndef format_gitlab_row\ndef filter_gitlab_row\n def filter\ndef to_int\nclass AICodeRatioData\n def __init__\n def loaddata\n def user_email_department_map\n def merge_commits\nclass AICodeRatioAnalysis\n def __init__\n def __getattr__\n def calc_user_commit_code\n def calc_accepted_code\n def calc_user_ai_gen_ratio\n def calc_stat\n  def calc\n```\n",
    "input_events": "User edited \"copilot_dashboard_analysis/ai_code_ratio.py\":\n```diff\n@@ -34,7 +34,7 @@\n     'python': {\n         'extensions': ['.py'],\n         'excluded_files': ['/migrations/'],\n-        'included_patterns': ['copilot'],\n+        'included_patterns': ['copilot']\n     },\n     'go': {\n         'extensions': ['.go'],\n\n```",
    "input_excerpt": "```copilot_dashboard_analysis/copilot_dashboard_analysis/ai_code_ratio.py\nfrom datautils.pandas import df_from_sql_if_not_exists\n\nfrom copilot_dashboard_analysis.config import Config\nfrom copilot_dashboard_analysis.sqls.ai_code_ratio import (\n    sql_ai_generated_code, sql_gerrit_changes, sql_gitlab_commits)\n\n_cache_dir = pathlib.Path(__file__).parent.parent / '.cache_data'\n\n_very_large_repos = [\n<|editable_region_start|>\n    'git@gitlab.chehejia.com:emb_group/emb_project.git',\n    'git@gitlab.chehejia.com:qcraft_external/vehicles.git',\n    'git@gitlab.chehejia.com:wuwenze_verify/kernel_monitor/linux-6.12.13.git',\n    'git@gitlabee.chehejia.com:rust-lang/crates.io-index.git',\n    'git@gitlab.chehejia.com:ad/production/lios/mcu/ad5_max_mcu_tc397.git',\n    'git@gitlab.chehejia.com:battery_management_system_project/supplier_project/x04.git',\n    'git@gitlab.chehejia.com:huangtianyuan/genv2_tms.git',\n]\n\n_common_generated_file_patterns = [\n    '/COMMIT_MSG',  # gerrit commit message\n    'generated_',\n    'grpc.pb',\n    'mock_',\n]\n\n_languages = {\n    'python': {\n        'extensions': ['.py'],\n        'excluded_files': ['/migrations/'],\n        'included_patterns': ['copilot']<|user_cursor_is_here|>\n    },\n    'go': {\n        'extensions': ['.go'],\n        'excluded_files': [\n            '/ent/',  # ent.go framework\n        ],\n    },\n    'javascript': {\n        'extensions': ['.js', '.jsx'],\n        'excluded_files': [\n            'node_modules',\n            'generated_',\n            'mock_',\n        ],\n    },\n    'typescript': {\n        'extensions': ['.ts', '.tsx'],\n<|editable_region_end|>\n        'excluded_files': [\n            'node_modules',\n            'generated_',\n            'mock_',\n        ],\n    },\n    'rust': {\n        'extensions': ['.rs'],\n```",
    "speculated_output": "<|editable_region_start|>\n    'git@gitlab.chehejia.com:emb_group/emb_project.git',\n    'git@gitlab.chehejia.com:qcraft_external/vehicles.git',\n    'git@gitlab.chehejia.com:wuwenze_verify/kernel_monitor/linux-6.12.13.git',\n    'git@gitlabee.chehejia.com:rust-lang/crates.io-index.git',\n    'git@gitlab.chehejia.com:ad/production/lios/mcu/ad5_max_mcu_tc397.git',\n    'git@gitlab.chehejia.com:battery_management_system_project/supplier_project/x04.git',\n    'git@gitlab.chehejia.com:huangtianyuan/genv2_tms.git',\n]\n\n_common_generated_file_patterns = [\n    '/COMMIT_MSG',  # gerrit commit message\n    'generated_',\n    'grpc.pb',\n    'mock_',\n]\n\n_languages = {\n    'python': {\n        'extensions': ['.py'],\n        'excluded_files': ['/migrations/'],\n        'included_patterns': ['copilot']<|user_cursor_is_here|>\n    },\n    'go': {\n        'extensions': ['.go'],\n        'excluded_files': [\n            '/ent/',  # ent.go framework\n        ],\n    },\n    'javascript': {\n        'extensions': ['.js', '.jsx'],\n        'excluded_files': [\n            'node_modules',\n            'generated_',\n            'mock_',\n        ],\n    },\n    'typescript': {\n        'extensions': ['.ts', '.tsx'],\n<|editable_region_end|>",
    }
    m = get_llm()
    result = await m.raw_generate(None, **case1)
    print('llm result:\n', result)
    choices = result.choices
    if len(choices):
        choice = choices[0]
        print('choice', choice)

# zed
# await test_zed('prod.zed-7B')


test_data = {
    'event':  "// User edited \"services/copilot/server/version.go\":\n// ```diff\n// -\t_, err := s.App.PublicConstClient.GetYAMLFile(uri, &version)\n// +\t_, err := \ts.App.PublicConstClient.GetYAMLFile(uri, &version)\n// ```\n",

    'editable': "func (s *App) GetAgentVersion(uri string) (*types.AgentVersion, error) {\n\n\tvar version types.AgentVersion\n\t_, err := \t<|user_cursor_is_here|>s.App.PublicConstClient.GetYAMLFile(uri, &version)\n\tif err != nil {\n\t\treturn nil, err\n\t}\n\treturn &version, nil\n}",

    'editable_prefix':  "package server\n\nimport (\n\t\"fmt\"\n\n\t\"github.com/gin-gonic/gin\"\n\n\t\"ep-services/pkg/lib/log\"\n\t\"ep-services/services/copilot/server/types\"\n\t\"ep-services/utils\"\n)\n\nconst (\n\tMODEL_PARAMS_CONFIG_URI = \"/consts/codebuddy/versions/model_params.yaml\"\n\tVERSION_CONFIG_URI      = \"/consts/codebuddy/versions/agent_00001.yaml\"\n)\n\nvar VERSION_CONFIG_URIS = []string{\n\n\t\"/consts/codebuddy/versions/model_param_groups.yaml\",\n\t\"/consts/codebuddy/versions/user_groups.yaml\",\n\t\"/consts/codebuddy/versions/agent_00002.yaml\",\n}\n\n",

    'editable_suffix': "\nfunc (s *App) GetModelParams(uri string) (*types.ModelParams, error) {\n\tvar modelParams types.ModelParams\n\t_, err := s.App.PublicConstClient.GetYAMLFile(uri, &modelParams)\n\tif err != nil {\n\t\treturn nil, err\n\t}\n\n\treturn &modelParams, nil\n}\n\nfunc (s *App) HandlerAgentVersion(c *gin.Context) {\n\n\tusername := c.Query(\"username\")\n\tversionConfigUrl := c.DefaultQuery(\"versionConfigUrl\", VERSION_CONFIG_URI)\n\tversionInfo, err := s.GetAgentVersion(versionConfigUrl)\n\tif err != nil {\n\t\tc.Error(err)\n\t\treturn\n\t}\n\tif detail, ok := versionInfo.Users[username]; ok {\n\t\tlog.Info().Msgf(\"user %s version detail: %s\", username, detail)\n\t\tc.JSON(200, gin.H{\n\t\t\t\"version\": detail,\n\t\t})\n\t\treturn\n\t}\n\tuser, err := s.getPortalUser(types.UserInfo{Name: username, Email: \"\"})\n\tif err != nil {\n\t\tlog.Warn().Msgf(\"get user info failed: %s\", err.Error())\n\t\tc.JSON(200, gin.H{\n\t\t\t\"version\": versionInfo.Default,\n\t\t})\n\t\treturn\n\t}\n\tif user == nil || user.L2Department == \"\" {\n\t\tlog.Warn().Msgf(\"user department is empty\")\n\t\tc.JSON(200, gin.H{\n\t\t\t\"version\": versionInfo.Default,\n\t\t})\n\t\treturn\n\t}\n\tif detail, ok := versionInfo.Departments[user.L2Department]; ok {\n\t\tselectedVersion := utils.WeightedRandomSelect(detail.Versions, int64(user.UserID))\n\t\tlog.Info().Msgf(\"department %s selected version: %s\", user.L2Department, selectedVersion)\n\t\tc.JSON(200, gin.H{\n\t\t\t\"version\": selectedVersion,\n\t\t})\n\t\treturn\n\t}\n\tc.JSON(200, gin.H{\n\t\t\"version\": versionInfo.Default,\n\t})\n}\nfunc (s *App) HandleGetModelParams(c *gin.Context) {\n\tusername := c.Query(\"username\")\n\tversionConfigUrl := c.DefaultQuery(\"versionConfigUrl\", VERSION_CONFIG_URI)\n\tmodelParamsConfigUrl := c.DefaultQuery(\"modelParamsConfigUrl\", MODEL_PARAMS_CONFIG_URI)\n\tdepartmentInfo, err := s.GetAgentVersion(versionConfigUrl)\n\tif err != nil {\n\t\tc.Error(err)\n\t\treturn\n\t}\n\tmodelParamsInfo, err := s.GetModelParams(modelParamsConfigUrl)\n\tif err != nil {\n\t\tc.Error(err)\n\t\treturn\n\t}\n\n\tdefaultModelParam, ok := modelParamsInfo.ModelParams[modelParamsInfo.Default]\n\tif !ok {\n\t\tc.Error(fmt.Errorf(\"model params not found for default key\"))\n\t\treturn\n\t}\n\tuser, err := s.getPortalUser(types.UserInfo{Name: username, Email: \"\"})\n\tif err != nil {\n\t\tlog.Warn().Msgf(\"get user info failed: %s\", err.Error())\n\t\tc.JSON(200, gin.H{\n\t\t\t\"model_params\": defaultModelParam,\n\t\t})\n\t\treturn\n\t}\n\tif user == nil || user.L2Department == \"\" {\n\t\tlog.Warn().Msgf(\"user department is empty\")\n\t\tc.JSON(200, gin.H{\n\t\t\t\"model_params\": defaultModelParam,\n\t\t})\n\t\treturn\n\t}\n\tif versions, ok := departmentInfo.Departments[user.L2Department]; ok {\n\t\tif len(versions.ModelParams) == 0 {\n\t\t\tlog.Warn().Msgf(\"model params is empty\")\n\t\t\tc.JSON(200, gin.H{\n\t\t\t\t\"model_params\": defaultModelParam,\n\t\t\t})\n\t\t\treturn\n\t\t}\n\t\tselectedModelParamVersion := utils.WeightedRandomSelect(versions.ModelParams, int64(user.UserID))\n\t\tif selectedModelParam, ok := modelParamsInfo.ModelParams[selectedModelParamVersion]; ok {\n\t\t\tlog.Info().Msgf(\"department %s selected model param: %s\", user.L2Department, selectedModelParamVersion)\n\t\t\tc.JSON(200, gin.H{\n\t\t\t\t\"model_params\": selectedModelParam,\n\t\t\t})\n\t\t\treturn\n\t\t}\n\t}\n\tc.JSON(200, gin.H{\n\t\t\"model_params\": defaultModelParam,\n\t})\n}\n\nfunc (s *App) HandleCodeFactoryVersion(c *gin.Context) {\n\tusername := c.Query(\"username\")\n\tversionConfigUrl := c.DefaultQuery(\"versionConfigUrl\", VERSION_CONFIG_URI)\n\tversionInfo, err := s.GetAgentVersion(versionConfigUrl)\n\tif err != nil {\n\t\tc.Error(err)\n\t\treturn\n\t}\n\n\tuser, err := s.getPortalUser(types.UserInfo{Name: username, Email: \"\"})\n\tif err != nil {\n\t\tlog.Warn().Msgf(\"get user info failed: %s\", err.Error())\n\t\tc.JSON(200, gin.H{\n\t\t\t\"version\": versionInfo.CodeFactoryDefault,\n\t\t})\n\t\treturn\n\t}\n\tif user == nil || user.L2Department == \"\" {\n\t\tlog.Warn().Msgf(\"user department is empty\")\n\t\tc.JSON(200, gin.H{\n\t\t\t\"version\": versionInfo.CodeFactoryDefault,\n\t\t})\n\t\treturn\n\t}\n\tif detail, ok := versionInfo.Departments[user.L2Department]; ok {\n\t\tselectedVersion := utils.WeightedRandomSelect(detail.CodeFactoryVersions, int64(user.UserID))\n\t\tlog.Info().Msgf(\"department %s selected version: %s\", user.L2Department, selectedVersion)\n\t\tc.JSON(200, gin.H{\n\t\t\t\"version\": selectedVersion,\n\t\t})\n\t\treturn\n\t}\n\n\tc.JSON(200, gin.H{\n\t\t\"version\": versionInfo.CodeFactoryDefault,\n\t})\n}\n\n// for agent_00002.yaml\nfunc (s *App) GetVersionConfig(paths []string) (*types.VersionConfig, error) {\n\tvar version types.VersionConfig\n\t_, err := s.App.PublicConstClient.GetMoreYAMLFiles(paths, &version)\n\tif err != nil {\n\t\treturn nil, err\n\t}\n\treturn &version, nil\n}\n\n// component: codebuddy, codebuddy_agent, codefactory\nfunc (s *App) HandleVersion(c *gin.Context) {\n\tusername := c.PostForm(\"username\")\n\tcomponent := c.PostForm(\"component\")\n\tpaths := c.PostFormArray(\"paths\")\n\n\tif len(paths) == 0 {\n\t\tpaths = VERSION_CONFIG_URIS\n\t}\n\n\tversionConfig, err := s.GetVersionConfig(paths)\n\tif err != nil {\n\t\tc.Error(err)\n\t\treturn\n\t}\n\t// special users\n\tif config, ok := versionConfig.Users[username]; ok {\n\t\tc.JSON(200, gin.H{\n\t\t\t\"version\": config[component],\n\t\t})\n\t\treturn\n\t}\n\n\t// get default\n\tdefaultVersion := versionConfig.Default[component]\n\tuser, err := s.getPortalUser(types.UserInfo{Name: username, Email: \"\"})\n\tif err != nil {\n\t\tlog.Warn().Msgf(\"get user info failed: %s\", err.Error())\n\t\tc.JSON(200, gin.H{\n\t\t\t\"version\": defaultVersion,\n\t\t})\n\t\treturn\n\t}\n\n\tif user == nil || user.L2Department == \"\" {\n\t\tlog.Warn().Msgf(\"user department is empty\")\n\t\tc.JSON(200, gin.H{\n\t\t\t\"version\": defaultVersion,\n\t\t})\n\t\treturn\n\t}\n\n\tif department, ok := versionConfig.Departments[user.L2Department]; ok {\n\t\tif components, ok := department[component]; ok {\n\t\t\tres := make(map[string]any)\n\t\t\tfor k, v := range components {\n\t\t\t\trandSeed := int64(user.UserID)\n\t\t\t\tif k != \"versions\" {\n\t\t\t\t\trandSeed = -1\n\t\t\t\t}\n\t\t\t\tselectedVersion := utils.WeightedRandomSelect(v, randSeed)\n\t\t\t\tres[k] = selectedVersion\n\t\t\t}\n\t\t\tc.JSON(200, gin.H{\n\t\t\t\t\"version\": res,\n\t\t\t})\n\t\t\treturn\n\t\t}\n\t}\n\tc.JSON(200, gin.H{\n\t\t\"version\": defaultVersion,\n\t})\n}\n"
}

async def test_codebuddy_predict(instance, config_path=None):
    await load_model_by_instance(instance, config_path=config_path)

    m = get_llm()
    input_events = test_data.get('event', '')
    editable = test_data.get('editable', '')
    editable_prefix = test_data.get('editable_prefix', '')
    editable_suffix = test_data.get('editable_suffix', '')
    input_excerpt = extract_input_excerpt(editable, editable_prefix,
                                          editable_suffix)
    original_draft_text = gen_predict_draft(editable, editable_suffix)

    start_time = time.perf_counter()
    result = await m.raw_generate(None,
                                          outline='',
                                          input_events=input_events,
                                          input_excerpt=input_excerpt,
                                          speculated_output='',
                                          original_draft_text=original_draft_text)
    print('llm result:\n', result)
    choices = result.choices
    if len(choices):
        choice = choices[0]
        print('choice', choice)
        print('='*30)
        print(choice.text)

    duration = time.perf_counter() - start_time
    print(f'duration {duration} seconds')

# await test_codebuddy_predict('prod.zed-7B', 'conf/fulledit.json')


async def test_predict_api(instance, config_path=None):
    await load_model_by_instance(instance, config_path=config_path)

    app = FastAPI()
    setup_zed_apis(app)
    client = TestClient(app)

    response = client.post("/codebuddy/predict", json=test_data)
    print(f"状态码: {response.status_code}")
    print(f"响应内容: {response.json()}")

# await test_predict_api('prod.zed-7B', 'conf/fulledit.json')
