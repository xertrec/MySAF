package com.uab.mysaf.ui.chat

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.IntrinsicSize
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.LinkAnnotation
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.TextLinkStyles
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.text.withLink
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.em
import androidx.compose.ui.unit.sp

/**
 * Lightweight Markdown renderer for SAFIA replies: headings, bullet / numbered lists, quotes,
 * code, tables, rules and inline bold / italic / code / links. The LLM writes Markdown; this
 * turns it into real formatting instead of showing raw asterisks.
 */

internal sealed interface MdBlock {
    data class Heading(val level: Int, val text: String) : MdBlock
    data class Paragraph(val text: String) : MdBlock
    data class ListItem(val marker: String, val ordered: Boolean, val indent: Int, val text: String) : MdBlock
    data class Quote(val text: String) : MdBlock
    data class Code(val text: String) : MdBlock
    data class Table(val header: List<String>, val rows: List<List<String>>) : MdBlock
    data object Rule : MdBlock
}

private val HEADING = Regex("""^(#{1,6})\s+(.*?)\s*#*\s*$""")
private val BULLET = Regex("""^(\s*)[-*+•]\s+(.*)$""")
private val ORDERED = Regex("""^(\s*)(\d{1,3})[.)]\s+(.*)$""")
private val RULE = Regex("""^\s*([-*_])(\s*\1){2,}\s*$""")
private val TABLE_SEPARATOR = Regex("""^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$""")

internal fun parseMarkdown(source: String): List<MdBlock> {
    val lines = source.replace("\r\n", "\n").split('\n')
    val blocks = mutableListOf<MdBlock>()
    val paragraph = mutableListOf<String>()

    fun flushParagraph() {
        if (paragraph.isNotEmpty()) {
            blocks += MdBlock.Paragraph(paragraph.joinToString("\n"))
            paragraph.clear()
        }
    }

    var i = 0
    while (i < lines.size) {
        val line = lines[i]
        val trimmed = line.trim()
        when {
            trimmed.startsWith("```") -> {
                flushParagraph()
                val code = mutableListOf<String>()
                i++
                while (i < lines.size && !lines[i].trim().startsWith("```")) code += lines[i++]
                blocks += MdBlock.Code(code.joinToString("\n"))
            }
            trimmed.isEmpty() -> flushParagraph()
            RULE.matches(line) -> {
                flushParagraph()
                blocks += MdBlock.Rule
            }
            HEADING.matches(trimmed) -> {
                flushParagraph()
                val m = HEADING.find(trimmed)!!
                blocks += MdBlock.Heading(m.groupValues[1].length, m.groupValues[2])
            }
            trimmed.startsWith("|") && i + 1 < lines.size && TABLE_SEPARATOR.matches(lines[i + 1]) -> {
                flushParagraph()
                val header = tableCells(trimmed)
                i += 2
                val rows = mutableListOf<List<String>>()
                while (i < lines.size && lines[i].trim().startsWith("|")) rows += tableCells(lines[i++].trim())
                blocks += MdBlock.Table(header, rows)
                continue
            }
            BULLET.matches(line) -> {
                flushParagraph()
                val m = BULLET.find(line)!!
                blocks += MdBlock.ListItem("•", ordered = false, indent = m.groupValues[1].length / 2, text = m.groupValues[2])
            }
            ORDERED.matches(line) -> {
                flushParagraph()
                val m = ORDERED.find(line)!!
                blocks += MdBlock.ListItem("${m.groupValues[2]}.", ordered = true, indent = m.groupValues[1].length / 2, text = m.groupValues[3])
            }
            trimmed.startsWith(">") -> {
                flushParagraph()
                val quote = mutableListOf<String>()
                while (i < lines.size && lines[i].trim().startsWith(">")) {
                    quote += lines[i++].trim().removePrefix(">").trimStart()
                }
                blocks += MdBlock.Quote(quote.joinToString("\n"))
                continue
            }
            else -> {
                // A continuation line of a list item joins it instead of starting a paragraph.
                val last = blocks.lastOrNull()
                if (paragraph.isEmpty() && last is MdBlock.ListItem && line.startsWith("  ")) {
                    blocks[blocks.lastIndex] = last.copy(text = last.text + " " + trimmed)
                } else {
                    paragraph += trimmed
                }
            }
        }
        i++
    }
    flushParagraph()
    return blocks
}

private fun tableCells(row: String): List<String> =
    row.trim().removePrefix("|").removeSuffix("|").split('|').map { it.trim() }

/** Inline Markdown → styled text. Unmatched markers are dropped (`**`) or kept literally (`*`). */
internal fun inlineMarkdown(
    text: String,
    codeBackground: Color = Color.Unspecified,
    linkColor: Color = Color.Unspecified,
): AnnotatedString = buildAnnotatedString {
    appendInline(text, codeBackground, linkColor)
}

private fun AnnotatedString.Builder.appendInline(text: String, codeBg: Color, linkColor: Color) {
    var i = 0
    val plain = StringBuilder()
    fun flush() {
        if (plain.isNotEmpty()) {
            append(plain.toString())
            plain.clear()
        }
    }
    while (i < text.length) {
        val c = text[i]
        when {
            c == '\\' && i + 1 < text.length && text[i + 1] in "*_`[]()#~\\" -> {
                plain.append(text[i + 1]); i += 2
            }
            c == '`' -> {
                val end = text.indexOf('`', i + 1)
                if (end > i) {
                    flush()
                    withStyle(SpanStyle(fontFamily = FontFamily.Monospace, background = codeBg, fontSize = 0.92.em)) {
                        append(text.substring(i + 1, end))
                    }
                    i = end + 1
                } else {
                    plain.append(c); i++
                }
            }
            text.startsWith("**", i) || text.startsWith("__", i) -> {
                val marker = text.substring(i, i + 2)
                val end = text.indexOf(marker, i + 2)
                if (end > i + 2) {
                    flush()
                    withStyle(SpanStyle(fontWeight = FontWeight.Bold)) {
                        appendInline(text.substring(i + 2, end), codeBg, linkColor)
                    }
                    i = end + 2
                } else {
                    i += 2 // stray marker: drop it rather than showing asterisks
                }
            }
            text.startsWith("~~", i) -> {
                val end = text.indexOf("~~", i + 2)
                if (end > i + 2) {
                    flush()
                    withStyle(SpanStyle(textDecoration = TextDecoration.LineThrough)) {
                        appendInline(text.substring(i + 2, end), codeBg, linkColor)
                    }
                    i = end + 2
                } else {
                    i += 2
                }
            }
            c == '*' && i + 1 < text.length && !text[i + 1].isWhitespace() -> {
                val end = findItalicEnd(text, i + 1)
                if (end > 0) {
                    flush()
                    withStyle(SpanStyle(fontStyle = FontStyle.Italic)) {
                        appendInline(text.substring(i + 1, end), codeBg, linkColor)
                    }
                    i = end + 1
                } else {
                    plain.append(c); i++
                }
            }
            c == '[' -> {
                val close = text.indexOf("](", i + 1)
                val urlEnd = if (close > 0) text.indexOf(')', close + 2) else -1
                if (close > 0 && urlEnd > 0) {
                    flush()
                    val label = text.substring(i + 1, close)
                    val url = text.substring(close + 2, urlEnd).trim()
                    if (url.startsWith("http://") || url.startsWith("https://")) {
                        withLink(
                            LinkAnnotation.Url(
                                url,
                                TextLinkStyles(SpanStyle(color = linkColor, textDecoration = TextDecoration.Underline)),
                            ),
                        ) { appendInline(label, codeBg, linkColor) }
                    } else {
                        appendInline(label, codeBg, linkColor)
                    }
                    i = urlEnd + 1
                } else {
                    plain.append(c); i++
                }
            }
            else -> {
                plain.append(c); i++
            }
        }
    }
    flush()
}

/** Closing `*` for an italic run starting at [from]: not preceded by a space, not part of `**`. */
private fun findItalicEnd(text: String, from: Int): Int {
    var j = from
    while (j < text.length) {
        if (text[j] == '*' && !text[j - 1].isWhitespace() && !text.startsWith("**", j)) return j
        if (text[j] == '\n') return -1
        j++
    }
    return -1
}

/** Plain text without Markdown markers, for copying and sharing. */
internal fun markdownToPlainText(source: String): String =
    parseMarkdown(source).joinToString("\n\n") { block ->
        when (block) {
            is MdBlock.Heading -> inlineMarkdown(block.text).text
            is MdBlock.Paragraph -> inlineMarkdown(block.text).text
            is MdBlock.ListItem -> "  ".repeat(block.indent) + block.marker + " " + inlineMarkdown(block.text).text
            is MdBlock.Quote -> inlineMarkdown(block.text).text
            is MdBlock.Code -> block.text
            is MdBlock.Table -> (listOf(block.header) + block.rows)
                .joinToString("\n") { row -> row.joinToString(" · ") { inlineMarkdown(it).text } }
            MdBlock.Rule -> "—"
        }
    }
        // Consecutive list items read better on adjacent lines.
        .replace(Regex("""\n\n(?=\s*(•|\d+\.) )"""), "\n")
        .trim()

@Composable
internal fun MarkdownText(
    markdown: String,
    modifier: Modifier = Modifier,
    color: Color = MaterialTheme.colorScheme.onSurface,
    accent: Color = MaterialTheme.colorScheme.primary,
) {
    val blocks = remember(markdown) { parseMarkdown(markdown) }
    val codeBg = MaterialTheme.colorScheme.surfaceVariant
    val bodySize = 15.sp
    val bodyLine = 21.sp
    fun styled(text: String) = inlineMarkdown(text, codeBg, accent)

    Column(modifier, verticalArrangement = Arrangement.spacedBy(6.dp)) {
        blocks.forEachIndexed { index, block ->
            when (block) {
                is MdBlock.Heading -> Text(
                    styled(block.text),
                    modifier = Modifier.padding(top = if (index == 0) 0.dp else 4.dp),
                    fontSize = when (block.level) { 1 -> 19.sp; 2 -> 17.sp; else -> 16.sp },
                    lineHeight = 23.sp,
                    fontWeight = FontWeight.Bold,
                    color = color,
                )
                is MdBlock.Paragraph -> Text(styled(block.text), fontSize = bodySize, lineHeight = bodyLine, color = color)
                is MdBlock.ListItem -> Row(Modifier.padding(start = (block.indent * 14).dp)) {
                    Text(
                        block.marker,
                        modifier = Modifier.widthIn(min = if (block.ordered) 22.dp else 14.dp),
                        fontSize = bodySize,
                        lineHeight = bodyLine,
                        fontWeight = if (block.ordered) FontWeight.SemiBold else FontWeight.Bold,
                        color = accent,
                    )
                    Text(styled(block.text), fontSize = bodySize, lineHeight = bodyLine, color = color)
                }
                is MdBlock.Quote -> Row(Modifier.height(IntrinsicSize.Min)) {
                    Box(Modifier.width(3.dp).fillMaxHeight().background(accent.copy(alpha = 0.5f), RoundedCornerShape(2.dp)))
                    Text(
                        styled(block.text),
                        modifier = Modifier.padding(start = 10.dp),
                        fontSize = bodySize,
                        lineHeight = bodyLine,
                        fontStyle = FontStyle.Italic,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                is MdBlock.Code -> Text(
                    block.text,
                    modifier = Modifier
                        .fillMaxWidth()
                        .background(codeBg, RoundedCornerShape(8.dp))
                        .padding(10.dp),
                    fontFamily = FontFamily.Monospace,
                    fontSize = 13.sp,
                    lineHeight = 18.sp,
                    color = color,
                )
                is MdBlock.Table -> Column(
                    Modifier.fillMaxWidth().background(codeBg.copy(alpha = 0.5f), RoundedCornerShape(8.dp)).padding(8.dp),
                ) {
                    (listOf(block.header) + block.rows).forEachIndexed { rowIndex, row ->
                        if (rowIndex == 1) HorizontalDivider(Modifier.padding(vertical = 4.dp), color = MaterialTheme.colorScheme.outlineVariant)
                        Row(Modifier.fillMaxWidth().padding(vertical = 2.dp)) {
                            row.forEach { cell ->
                                Text(
                                    styled(cell),
                                    modifier = Modifier.weight(1f).padding(end = 6.dp),
                                    fontSize = 13.sp,
                                    lineHeight = 18.sp,
                                    fontWeight = if (rowIndex == 0) FontWeight.Bold else FontWeight.Normal,
                                    color = color,
                                )
                            }
                        }
                    }
                }
                MdBlock.Rule -> HorizontalDivider(Modifier.padding(vertical = 4.dp), color = MaterialTheme.colorScheme.outlineVariant)
            }
        }
    }
}
