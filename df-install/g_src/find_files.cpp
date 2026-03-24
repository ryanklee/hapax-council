#include "../game_g.h"
#include "../game_extv.h"

std::vector<std::filesystem::path> find_files_by_filter(std::function<bool(const std::filesystem::directory_entry &)> f) {
	std::vector<std::filesystem::path> ret;
	for (auto const &dir_entry : std::filesystem::directory_iterator{get_base_path()})
		{
		if (f(dir_entry))  ret.push_back(dir_entry.path());
		}
	for (auto const &dir_entry : std::filesystem::directory_iterator{get_pref_path()})
		{
		if (f(dir_entry))  ret.push_back(dir_entry.path());
		}
	}