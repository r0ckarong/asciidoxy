/*
 * Copyright (C) 2019, TomTom (http://tomtom.com).
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#include <array>
#include <type_traits>

namespace asciidoxy {
namespace tparam {

template<class T>
struct is_container : std::false_type {
};

template<typename T, typename N>
struct is_container<std::array<T, N>> : std::true_type {
};

/**
 * Check if the value is even.
 *
 * @param value The value to check.
 * @tparam T A numeric type.
 * @returns True if the value is even, false if it is not.
 */
template<typename T>
bool IsEven(T value);

/**
 * Simple mapping between keys and values.
 *
 * @tparam K Key type.
 * @tparam V Value type.
 */
template<typename K, class V>
struct Mapping {
  void Insert(const K& key, const V& value);
};

}  // namespace tparam
}  // namespace asciidoxy
