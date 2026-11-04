# Test Diff — ikinci-churn-veri-seti (red)

Yazan: backend-copilot (Haiku). Testler çalıştırılmadı (yalnızca ast.parse).

| AC | Test |
|---|---|
| arayüz | test_training_profiles::test_profiles_have_telco_and_openml_churn_with_openml_paths_and_target |
| AC-6 | test_training_profiles::test_ac6_unknown_dataset_exits_2_with_exact_line_and_writes_nothing |
| AC-7 | test_training_profiles::test_ac7_bad_input_exits_2_with_message_and_writes_nothing[dosya_yok/hedef_yok/tek_sinif/bos_veri] |
| AC-8 | test_training_profiles::test_ac8_failure_mid_training_keeps_previous_outputs_and_removes_tmp |
| AC-1/4/12 | test_training_profiles::test_ac1_ac4_ac12_smoke_training_writes_six_outputs_and_logs_summary |
| AC-1 (Telco hash) | test_training_profiles::test_ac1_real_root_telco_outputs_unchanged_after_smoke_training |
| AC-11 | test_training_profiles::test_ac11_two_smoke_runs_with_same_seed_give_same_best_roc_auc |
| AC-1 (eşik) | test_training_profiles::test_ac1_real_openml_metrics_meet_roc_auc_threshold |
| AC-2 | test_dataset_contract::test_ac2_endpoint_returns_200_for_each_dataset[6×2], test_ac2_openml_top_level_keys_equal_telco_keys[6] |
| AC-3 | test_dataset_contract::test_ac3_default_profile_is_telco_and_summary_is_ibm_telco |
| AC-5 | test_dataset_contract::test_ac5_* (4 test) |
| AC-9 | test_dataset_contract::test_ac9_unknown_dataset_env_raises_value_error_on_import (dosyanın sonunda, finally'de reload) |
| AC-10 | test_dataset_contract::test_ac10_missing_output_dir_returns_503_on_data_endpoints |

Not: AC-1 eşik testi ve AC-2/AC-5'in openml dalı, orkestratör tam eğitimi koşup `outputs/openml_churn/` üretene kadar kırmızı kalır.
