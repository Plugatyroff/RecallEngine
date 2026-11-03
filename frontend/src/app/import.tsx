import * as DocumentPicker from 'expo-document-picker';
import { router } from 'expo-router';
import * as WebBrowser from 'expo-web-browser';
import { useState } from 'react';
import { ActivityIndicator, ScrollView, View } from 'react-native';

import { Button, Label, Screen, SectionTitle } from '@/components/ui';
import { Spacing } from '@/constants/theme';
import { api, ApiError, type AnkiImportResult } from '@/services/api';

const ANKIWEB_SHARED_DECKS = 'https://ankiweb.net/shared/decks';

function summary(result: AnkiImportResult): string {
  const cards = `${result.cards_created} new card${result.cards_created === 1 ? '' : 's'}`;
  const updated = result.cards_updated ? `, ${result.cards_updated} updated` : '';
  const topics = result.topics_created ? ` in ${result.topics_created} new topic${result.topics_created === 1 ? '' : 's'}` : '';
  const reviews = result.reviews_imported ? `, with ${result.reviews_imported} past reviews` : '';
  return `Imported ${cards}${updated}${topics}${reviews}.`;
}

/** Get decks from AnkiWeb and import Anki deck files. */
export default function ImportScreen() {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [warnings, setWarnings] = useState<string[]>([]);

  const pickAndImport = async () => {
    const picked = await DocumentPicker.getDocumentAsync({ type: '*/*', copyToCacheDirectory: true });
    if (picked.canceled) return;
    const file = picked.assets[0];
    if (!/\.(apkg|colpkg)$/i.test(file.name)) {
      setMessage(`"${file.name}" is not an Anki deck file (.apkg or .colpkg).`);
      return;
    }
    setBusy(true);
    setMessage(`Importing ${file.name}… large decks can take a minute.`);
    setWarnings([]);
    try {
      const result = await api.importAnki(file);
      setMessage(summary(result));
      setWarnings(result.warnings);
    } catch (e) {
      setMessage(e instanceof ApiError ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Screen>
      <ScrollView contentContainerStyle={{ gap: Spacing.two }}>
        <SectionTitle>1. Download a deck</SectionTitle>
        <Label muted>Browse AnkiWeb&apos;s shared decks and download one. It is saved as an .apkg file.</Label>
        <View style={{ flexDirection: 'row' }}>
          <Button title="Open AnkiWeb shared decks" onPress={() => WebBrowser.openBrowserAsync(ANKIWEB_SHARED_DECKS)} />
        </View>

        <SectionTitle>2. Import it</SectionTitle>
        <Label muted>Choose the downloaded .apkg file (or a .colpkg exported from Anki). Its decks become topics.</Label>
        <View style={{ flexDirection: 'row' }}>
          <Button primary title={busy ? 'Importing…' : 'Choose deck file'} onPress={pickAndImport} disabled={busy} />
        </View>

        {busy ? <ActivityIndicator /> : null}
        {message ? <Label>{message}</Label> : null}
        {warnings.map((warning) => (
          <Label key={warning} muted>
            ⚠ {warning}
          </Label>
        ))}
        {message && !busy && !warnings.length && message.startsWith('Imported') ? (
          <View style={{ flexDirection: 'row' }}>
            <Button title="Back to topics" onPress={() => router.back()} />
          </View>
        ) : null}
      </ScrollView>
    </Screen>
  );
}
