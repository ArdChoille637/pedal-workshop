import { Settings as SettingsIcon } from "lucide-react";

export default function SettingsPage() {
  return (
    <div className="p-8 max-w-2xl">
      <h1 className="text-2xl font-bold mb-6">Settings</h1>

      <div className="bg-white rounded-lg border divide-y">
        <div className="p-4">
          <h2 className="font-semibold flex items-center gap-2 mb-4">
            <SettingsIcon className="w-4 h-4" />
            Supplier API Keys
          </h2>
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Mouser API Key
              </label>
              <input
                type="password"
                placeholder="Enter your Mouser API key"
                className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
              <p className="text-xs text-gray-400 mt-1">
                Get a free API key from the Mouser developer portal
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                DigiKey Client ID
              </label>
              <input
                type="password"
                placeholder="Enter your DigiKey client ID"
                className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                DigiKey Client Secret
              </label>
              <input
                type="password"
                placeholder="Enter your DigiKey client secret"
                className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
          </div>
        </div>

        <div className="p-4">
          <h2 className="font-semibold mb-4">Polling Configuration</h2>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Default Poll Interval
            </label>
            <select className="border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500">
              <option value="3600">Every hour</option>
              <option value="21600">Every 6 hours</option>
              <option value="43200">Every 12 hours</option>
              <option value="86400">Daily</option>
              <option value="604800">Weekly</option>
            </select>
          </div>
        </div>

        <div className="p-4">
          <p className="text-xs text-gray-400">
            API keys are stored in the .env file at workshop/.env.
            Changes here are for display only - edit .env directly to persist.
          </p>
        </div>
      </div>
    </div>
  );
}
