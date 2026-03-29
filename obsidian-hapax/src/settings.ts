import { App, PluginSettingTab, Setting } from "obsidian";
import type HapaxPlugin from "./main";

export class HapaxSettingTab extends PluginSettingTab {
  plugin: HapaxPlugin;

  constructor(app: App, plugin: HapaxPlugin) {
    super(app, plugin);
    this.plugin = plugin;
  }

  display(): void {
    const { containerEl } = this;
    containerEl.empty();
    containerEl.createEl("h2", { text: "Hapax Settings" });

    new Setting(containerEl)
      .setName("Logos API URL")
      .setDesc("Base URL for the Logos API (e.g. http://localhost:8051)")
      .addText((text) =>
        text
          .setPlaceholder("http://localhost:8051")
          .setValue(this.plugin.settings.logosApiUrl)
          .onChange(async (value) => {
            this.plugin.settings.logosApiUrl = value.trim();
            this.plugin.client.updateBaseUrl(value.trim());
            await this.plugin.saveSettings();
          }),
      );

    new Setting(containerEl)
      .setName("Refresh interval (seconds)")
      .setDesc("How often the panel auto-refreshes (10–120s)")
      .addSlider((slider) =>
        slider
          .setLimits(10, 120, 5)
          .setValue(this.plugin.settings.refreshInterval)
          .setDynamicTooltip()
          .onChange(async (value) => {
            this.plugin.settings.refreshInterval = value;
            this.plugin.restartRefreshTimer();
            await this.plugin.saveSettings();
          }),
      );

    new Setting(containerEl)
      .setName("Show on unknown notes")
      .setDesc("Display the panel even when the note type cannot be determined")
      .addToggle((toggle) =>
        toggle
          .setValue(this.plugin.settings.showOnUnknownNotes)
          .onChange(async (value) => {
            this.plugin.settings.showOnUnknownNotes = value;
            await this.plugin.saveSettings();
          }),
      );
  }
}
