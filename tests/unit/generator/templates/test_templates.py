# Copyright (C) 2019, TomTom (http://tomtom.com).
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Test the templates used for C++ code."""

import pytest


@pytest.mark.parametrize("element_name,language,expected_result", [
    ("asciidoxy::geometry::Coordinate", "cpp", "fragments/cpp/class.adoc"),
    ("asciidoxy::traffic::TrafficEvent::Severity", "cpp", "fragments/cpp/enum.adoc"),
    ("asciidoxy::system::Service", "cpp", "fragments/cpp/interface.adoc"),
    ("asciidoxy::traffic::TrafficEvent::TrafficEventData", "cpp", "fragments/cpp/struct.adoc"),
    ("asciidoxy::traffic::TpegCauseCode", "cpp", "fragments/cpp/alias.adoc"),
    ("asciidoxy::traffic::Delay", "cpp", "fragments/cpp/typedef.adoc"),
    ("DEFAULT_CB", "cpp", "fragments/cpp/function_typedef.adoc"),
    ("asciidoxy::wifi::ESP32WiFiProtocol", "cpp", "fragments/cpp/enum_with_or.adoc"),
    ("asciidoxy::traffic::TrafficEvent", "cpp", "fragments/cpp/nested.adoc"),
    ("asciidoxy::traffic::TrafficEvent::SharedData", "cpp", "fragments/cpp/function.adoc"),
    ("asciidoxy::system::CreateService", "cpp", "fragments/cpp/free_function.adoc"),
    ("asciidoxy::geometry::Point::increment", "cpp", "fragments/cpp/function_default_value.adoc"),
    ("asciidoxy::tparam::IsEven", "cpp", "fragments/cpp/function_tparam.adoc"),
    ("asciidoxy::tparam::Mapping", "cpp", "fragments/cpp/class_tparam.adoc"),
    ("com.asciidoxy.geometry.Coordinate", "java", "fragments/java/class.adoc"),
    ("com.asciidoxy.traffic.TrafficEvent.Severity", "java", "fragments/java/enum.adoc"),
    ("com.asciidoxy.system.Service", "java", "fragments/java/interface.adoc"),
    ("com.asciidoxy.traffic.TrafficEvent", "java", "fragments/java/nested.adoc"),
    ("ADTrafficEvent", "objc", "fragments/objc/protocol.adoc"),
    ("ADSeverity", "objc", "fragments/objc/enum.adoc"),
    ("ADCoordinate", "objc", "fragments/objc/interface.adoc"),
    ("OnTrafficEventCallback", "objc", "fragments/objc/block.adoc"),
    ("TpegCauseCode", "objc", "fragments/objc/typedef.adoc"),
    ("asciidoxy.geometry.Coordinate", "python", "fragments/python/class.adoc"),
    ("asciidoxy.traffic.TrafficEvent.update", "python", "fragments/python/function.adoc"),
    ("asciidoxy.default_values.Point.increment", "python",
     "fragments/python/function_default_value.adoc"),
])
def test_fragment(generating_api, adoc_data, element_name, language, expected_result,
                  update_expected_results, doxygen_version):
    content = generating_api.insert(element_name, lang=language)

    expected_result_file = (adoc_data / expected_result).with_suffix(f".{doxygen_version}.adoc")
    if update_expected_results:
        expected_result_file.write_text(content, encoding="UTF-8")

    assert content == expected_result_file.read_text(encoding="UTF-8")


filtered_testdata = [
    ("asciidoxy::geometry::Coordinate", "cpp", {
        "members": {
            "name": "-Altitude",
            "prot": "ALL"
        }
    }, "fragments/cpp/class_filtered.adoc"),
    ("asciidoxy::traffic::TrafficEvent::Severity", "cpp", {
        "members": ["+Medium", "+High"]
    }, "fragments/cpp/enum_filtered.adoc"),
    ("asciidoxy::system::Service", "cpp", {
        "members": "+Start"
    }, "fragments/cpp/interface_filtered.adoc"),
    ("asciidoxy::traffic::TrafficEvent::TrafficEventData", "cpp", {
        "members": "-delay"
    }, "fragments/cpp/struct_filtered.adoc"),
    ("asciidoxy::traffic::TrafficEvent", "cpp", {
        "members": {
            "prot": "ALL",
            "name": "-TrafficEventData",
        },
    }, "fragments/cpp/nested_filtered.adoc"),
    ("asciidoxy::traffic::TrafficEvent::SharedData", "cpp", {
        "exceptions": "-std::"
    }, "fragments/cpp/function_filtered.adoc"),
    ("com.asciidoxy.geometry.Coordinate", "java", {
        "members": "-IsValid"
    }, "fragments/java/class_filtered.adoc"),
    ("com.asciidoxy.traffic.TrafficEvent.Severity", "java", {
        "members": "-Unknown"
    }, "fragments/java/enum_filtered.adoc"),
    ("com.asciidoxy.system.Service", "java", {
        "members": "Start"
    }, "fragments/java/interface_filtered.adoc"),
    ("com.asciidoxy.traffic.TrafficEvent", "java", {
        "members": "-Severity"
    }, "fragments/java/nested_filtered.adoc"),
    ("ADTrafficEvent", "objc", {
        "members": {
            "kind": "-property"
        }
    }, "fragments/objc/protocol_filtered.adoc"),
    ("ADSeverity", "objc", {
        "members": ["Low", "Medium"]
    }, "fragments/objc/enum_filtered.adoc"),
    ("ADCoordinate", "objc", {
        "members": {
            "kind": "property"
        }
    }, "fragments/objc/interface_filtered.adoc"),
    ("asciidoxy.geometry.Coordinate", "python", {
        "members": "-altitude"
    }, "fragments/python/class_filtered.adoc"),
    ("asciidoxy.traffic.TrafficEvent.refresh_data", "python", {
        "exceptions": "NoDataError",
    }, "fragments/python/function_filtered.adoc"),
]


@pytest.mark.parametrize("element_name,language,filter_spec,expected_result", filtered_testdata)
def test_global_filter(generating_api, adoc_data, element_name, language, filter_spec,
                       expected_result, update_expected_results, doxygen_version):
    generating_api.filter(**filter_spec)
    content = generating_api.insert(element_name, lang=language)

    expected_result_file = (adoc_data / expected_result).with_suffix(f".{doxygen_version}.adoc")
    if update_expected_results:
        expected_result_file.write_text(content, encoding="UTF-8")

    assert content == expected_result_file.read_text(encoding="UTF-8")


@pytest.mark.parametrize("element_name,language,filter_spec,expected_result", filtered_testdata)
def test_local_filter(generating_api, adoc_data, element_name, language, filter_spec,
                      expected_result, update_expected_results, doxygen_version):
    content = generating_api.insert(element_name, lang=language, **filter_spec)

    expected_result_file = (adoc_data / expected_result).with_suffix(f".{doxygen_version}.adoc")
    if update_expected_results:
        expected_result_file.write_text(content, encoding="UTF-8")

    assert content == expected_result_file.read_text(encoding="UTF-8")


@pytest.mark.parametrize("element_name,source,target,expected_result", [
    ("ADTrafficEvent", "objc", "swift", "fragments/swift/transcoded_protocol.adoc"),
    ("ADSeverity", "objc", "swift", "fragments/swift/transcoded_enum.adoc"),
    ("ADCoordinate", "objc", "swift", "fragments/swift/transcoded_interface.adoc"),
    ("OnTrafficEventCallback", "objc", "swift", "fragments/swift/transcoded_block.adoc"),
    ("TpegCauseCode", "objc", "swift", "fragments/swift/transcoded_typedef.adoc"),
    ("com.asciidoxy.geometry.Coordinate", "java", "kotlin",
     "fragments/kotlin/transcoded_class.adoc"),
    ("com.asciidoxy.traffic.TrafficEvent.Severity", "java", "kotlin",
     "fragments/kotlin/transcoded_enum.adoc"),
    ("com.asciidoxy.system.Service", "java", "kotlin",
     "fragments/kotlin/transcoded_interface.adoc"),
    ("com.asciidoxy.traffic.TrafficEvent", "java", "kotlin",
     "fragments/kotlin/transcoded_nested.adoc"),
])
def test_transcoded_fragment(generating_api, adoc_data, element_name, source, target,
                             expected_result, update_expected_results, doxygen_version):
    generating_api.language(target, source=source)
    content = generating_api.insert(element_name)

    expected_result_file = (adoc_data / expected_result).with_suffix(f".{doxygen_version}.adoc")
    if update_expected_results:
        expected_result_file.write_text(content, encoding="UTF-8")

    assert content == expected_result_file.read_text(encoding="UTF-8")
